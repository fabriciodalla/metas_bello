from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from api.config import settings
from api.services.erp.connection import get_erp_connection, ErpConfigError, ErpQueryError
from api.services.erp.normalize import normalize_name


@dataclass(frozen=True)
class AccumulatedRow:
    supervisor_code: str
    seller_code: str
    seller_name: str
    seller_name_normalized: str
    clifor: str
    cnpj: str
    client_name: str
    month: date
    product_name: str
    product_name_normalized: str
    total_kg: Decimal
    total_value: Decimal
    company_code: str


ACCUMULATED_QUERY = """
WITH sup_map_geral AS (
    SELECT
        sv.nk_vendedor,
        ('B.F.' || sv.cd_emprvend) AS nk_empresa,
        MIN(sv.nk_supervisor)      AS nk_supervisor
    FROM {schema}.st_supervisorvenda sv
    WHERE sv.dt_cancelamento IS NULL
      AND sv.nk_supervisor IN (
            'B.F.434','B.F.292','B.F.80','B.F.229',
            'B.F.212','B.F.293','B.F.446','B.F.1017','B.F.253'
      )
      AND sv.nk_vendedor <> 'B.F.1401'
    GROUP BY sv.nk_vendedor, ('B.F.' || sv.cd_emprvend)
),
sup_map_1401_ativo AS (
    SELECT
        sv.nk_vendedor,
        ('B.F.' || sv.cd_emprvend) AS nk_empresa,
        MIN(sv.nk_supervisor)      AS nk_supervisor
    FROM {schema}.st_supervisorvenda sv
    WHERE sv.nk_vendedor = 'B.F.1401'
      AND sv.dt_cancelamento IS NULL
      AND sv.nk_supervisor IN (
            'B.F.434','B.F.292','B.F.80','B.F.229',
            'B.F.212','B.F.293','B.F.446','B.F.1017','B.F.253'
      )
    GROUP BY sv.nk_vendedor, ('B.F.' || sv.cd_emprvend)
),
sup_map_1401_cancelado AS (
    SELECT
        sv.nk_vendedor,
        ('B.F.' || sv.cd_emprvend) AS nk_empresa,
        MIN(sv.nk_supervisor)      AS nk_supervisor
    FROM {schema}.st_supervisorvenda sv
    WHERE sv.nk_vendedor = 'B.F.1401'
      AND sv.dt_cancelamento IS NOT NULL
      AND sv.nk_supervisor IN (
            'B.F.434','B.F.292','B.F.80','B.F.229',
            'B.F.212','B.F.293','B.F.446','B.F.1017','B.F.253'
      )
    GROUP BY sv.nk_vendedor, ('B.F.' || sv.cd_emprvend)
),
sup_map AS (
    SELECT nk_vendedor, nk_empresa, nk_supervisor FROM sup_map_geral
    UNION ALL
    SELECT nk_vendedor, nk_empresa, nk_supervisor FROM sup_map_1401_ativo
    UNION ALL
    SELECT c.nk_vendedor, c.nk_empresa, c.nk_supervisor
    FROM sup_map_1401_cancelado c
    WHERE NOT EXISTS (
        SELECT 1 FROM sup_map_1401_ativo a
        WHERE a.nk_vendedor = c.nk_vendedor AND a.nk_empresa = c.nk_empresa
    )
)
SELECT
    sup.nk_supervisor,
    vendin.nk_vendedor,
    vend.nm_clifor AS nome_vendedor,
    cli.cd_clifor,
    cli.nr_cgccpf AS cnpj,
    cli.nm_fantasia AS nome_cliente,
    DATE_TRUNC('MONTH', vendin.dt_emissao)::DATE AS dt_mes,
    item.ds_subgrupo,
    SUM(vendin.qt_nota)          AS total_ps_atendido,
    SUM(vendin.vl_tot_item_cont) AS total_vl_movtocontabil,
    vendin.nk_empresa
FROM stage_comercial.st_venda_dinamica vendin
INNER JOIN sup_map sup
    ON vendin.nk_vendedor = sup.nk_vendedor AND vendin.nk_empresa = sup.nk_empresa
INNER JOIN {schema}.st_vendedor vend
    ON vendin.nk_vendedor = vend.nk_vendedor
INNER JOIN {schema}.st_item item
    ON vendin.nk_item = item.nk_item
LEFT JOIN {schema}.st_cliforendereco cfend
    ON vendin.nk_cliforendereco = cfend.nk_cliforendereco
LEFT JOIN {schema}.st_clifor cli
    ON cfend.nk_clifor = cli.nk_clifor
WHERE vendin.dt_emissao >= %(start_date)s
  AND vend.ds_estado NOT LIKE '%%SAO PAULO%%'
  AND CAST(vendin.cd_movimentacao AS TEXT) NOT LIKE '69%%'
  AND CASE
    WHEN vendin.nk_empresa IN ('B.F.1','B.F.2','B.F.4','B.F.8','B.F.9','B.F.11','B.F.16','B.F.17','B.F.20','B.F.22','B.F.26','B.F.29','B.F.30','B.F.70','B.F.80','B.F.100') AND vendin.cd_movimentacao IN (3067,7585) THEN 'N'
    WHEN vendin.nk_empresa IN ('B.F.300','B.F.301') AND vendin.cd_movimentacao IN (796,7770,9890,7771) THEN 'N'
    WHEN vendin.nk_empresa IN ('B.F.350','B.F.351','B.F.352','B.F.353','B.F.354') AND vendin.cd_movimentacao = 6970 THEN 'S'
    WHEN vendin.nk_empresa IN ('B.F.1','B.F.2','B.F.4','B.F.8','B.F.9','B.F.11','B.F.16','B.F.17','B.F.20','B.F.22','B.F.26','B.F.29','B.F.30','B.F.70','B.F.80','B.F.100') AND vendin.cd_movimentacao IN (2901,5599,6970) THEN 'S'
    WHEN vendin.nk_empresa = 'B.F.330' AND vendin.cd_movimentacao = 2884 THEN 'S'
    WHEN vendin.nk_empresa = 'B.F.320' AND vendin.cd_movimentacao IN (796,5599,6550) THEN 'S'
    WHEN vendin.nk_empresa = 'B.F.320' AND vendin.cd_movimentacao IN (3162,7770,7771) THEN 'N'
    WHEN vendin.nk_item = 'B.F.3293422' THEN 'S'
    WHEN vendin.cd_movimentacao = 2332 AND vendin.cd_contacontabil = 6722 THEN 'N'
    WHEN vendin.cd_movimentacao IN (2235,7442) THEN 'N'
    WHEN vendin.cd_movimentacao = 7018 THEN 'S'
    WHEN vendin.cd_movimentacao = 7585 AND vendin.cd_contacontabil = 782 THEN 'N'
    WHEN vendin.nk_empresa = 'B.F.200' AND vendin.cd_movimentacao IN (7770,6003,796,558,6009) THEN 'S'
    WHEN vendin.cd_movimentacao IN (69,570,7570,796,7403,559,2635,6910,7806,558,2340,1090,1771,1778,4855,7075,7745,8745,7012,7009,7006,7015,8003,7710,6003,6007,8075,8076,40,7706,7707,4040,6013,1020,3026,3027,6010,2883,1050,6020,4041) THEN 'S'
    WHEN vendin.cd_movimentacao IN (4413,6011,6012,1235,1544,4412,6971,7585,7661,2533,2534,2535,2536,2543) THEN 'N'
    WHEN vendin.nk_empresa IN ('B.F.1','B.F.2','B.F.3','B.F.4','B.F.5','B.F.8','B.F.70','B.F.80','B.F.90','B.F.100','B.F.9','B.F.11','B.F.14') AND vendin.cd_contacontabil = 4073 THEN 'S'
    WHEN vendin.cd_contacontabil = 4411 AND vendin.cd_movimentacao IN (1000,1796) THEN 'S'
    WHEN vendin.nk_empresa = 'B.F.8' AND vendin.cd_contacontabil = 6104 THEN 'S'
    WHEN vendin.cd_contacontabil = 4051 AND vendin.cd_movimentacao IN (1776,1777,7002,7003,7008,7014,7033,8002,8008,8040,8042,8043) THEN 'S'
    WHEN vendin.cd_contacontabil = 4065 AND vendin.cd_movimentacao NOT IN (407,410,1779,1771) THEN 'S'
    WHEN vendin.nk_empresa IN ('B.F.1','B.F.2','B.F.5','B.F.6','B.F.7','B.F.9','B.F.11','B.F.12') AND vendin.cd_movimentacao IN (69,812,7075,7706,7780) THEN 'S'
    WHEN vendin.nk_empresa = 'B.F.11' AND vendin.cd_movimentacao IN (896,796,1771) THEN 'N'
    WHEN vendin.nk_empresa IN ('B.F.12','B.F.4','B.F.8','B.F.70','B.F.80','B.F.100') AND vendin.cd_movimentacao IN (796,1771) THEN 'S'
    WHEN vendin.nk_empresa IN ('B.F.200','B.F.202','B.F.203') AND vendin.cd_movimentacao IN (4040,7403) THEN 'S'
    WHEN vendin.nk_empresa = 'B.F.16' AND vendin.cd_movimentacao = 796 THEN 'S'
    WHEN vendin.nk_empresa = 'B.F.300' AND vendin.cd_movimentacao IN (2340,6910,7402,6025,112,7770,5599,6911,6915) THEN 'S'
    WHEN vendin.nk_empresa IN ('B.F.200','B.F.201','B.F.202','B.F.203','B.F.204') AND vendin.cd_movimentacao = 6006 THEN 'S'
    WHEN vendin.nk_empresa = 'B.F.12' AND vendin.cd_movimentacao = 250 THEN 'S'
    ELSE 'N'
  END = 'S'
GROUP BY
    sup.nk_supervisor, vendin.nk_vendedor, vend.nm_clifor,
    cli.cd_clifor, cli.nr_cgccpf, cli.nm_fantasia,
    item.ds_subgrupo, DATE_TRUNC('MONTH', vendin.dt_emissao)::DATE, vendin.nk_empresa
ORDER BY dt_mes, sup.nk_supervisor, ds_subgrupo
"""


def fetch_accumulated(start_date: str) -> list[AccumulatedRow]:
    schema = settings.erp_db_schema
    query = ACCUMULATED_QUERY.format(schema=schema)

    try:
        conn = get_erp_connection()
    except Exception as exc:
        raise ErpConfigError(f"Erro ao conectar no ERP: {exc}") from exc

    try:
        with conn.cursor() as cur:
            cur.execute(query, {"start_date": start_date})
            rows = []
            for r in cur.fetchall():
                kg = r[8]
                if kg is None:
                    continue
                rows.append(AccumulatedRow(
                    supervisor_code=str(r[0] or "").strip(),
                    seller_code=str(r[1] or "").strip(),
                    seller_name=str(r[2] or "").strip(),
                    seller_name_normalized=normalize_name(r[2]),
                    clifor=str(r[3] or "").strip(),
                    cnpj=str(r[4] or "").strip(),
                    client_name=str(r[5] or "").strip(),
                    month=r[6],
                    product_name=str(r[7] or "").strip(),
                    product_name_normalized=normalize_name(r[7]),
                    total_kg=Decimal(str(kg)),
                    total_value=Decimal(str(r[9] or 0)),
                    company_code=str(r[10] or "").strip(),
                ))
            return rows
    except Exception as exc:
        raise ErpQueryError(f"Erro ao consultar acumulado: {exc}") from exc
    finally:
        conn.close()
