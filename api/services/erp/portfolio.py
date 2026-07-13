from dataclasses import dataclass

from api.config import settings
from api.services.erp.connection import get_erp_connection, ErpConfigError, ErpQueryError
from api.services.erp.normalize import normalize_name


@dataclass(frozen=True)
class PortfolioRow:
    clifor: str
    cnpj: str
    client_name: str
    seller_name: str
    seller_name_normalized: str
    supervisor_code: str
    municipality: str
    state: str


PORTFOLIO_QUERY = """
SELECT DISTINCT ON (clifor.cd_clifor)
    clifor.cd_clifor          AS clifor,
    clifor.nr_cgccpf          AS cnpj,
    clifor.nm_clifor          AS nome_cliente,
    vendedor.nm_clifor        AS nome_vendedor,
    sup_map.nk_supervisor     AS nk_supervisor,
    endereco.ds_municipioibge AS municipio,
    endereco.ds_estado        AS estado
FROM {schema}.st_cliforendereco AS endereco
JOIN {schema}.st_clifor AS clifor
    ON clifor.nk_clifor = endereco.nk_clifor
JOIN {schema}.st_vendedor AS vendedor
    ON vendedor.nk_vendedor = endereco.nk_vendedor
JOIN {schema}.st_supervisorvenda AS sup_map
    ON sup_map.nk_vendedor = vendedor.nk_vendedor
WHERE endereco.st_ativo = 'S'
  AND clifor.ds_tp_clifor = 'Cliente'
  AND clifor.dt_venctocad IS NULL
  AND vendedor.nk_vendedor NOT IN (
      'B.F.60','B.F.65','B.F.1087','B.F.1089','B.F.1090',
      'B.F.1091','B.F.1092','B.F.1093','B.F.1364'
  )
  AND (
        (sup_map.nk_supervisor = 'B.F.229'
         AND endereco.ds_estado = 'GOIAS')
     OR (sup_map.nk_supervisor IN ('B.F.434','B.F.212','B.F.293','B.F.446','B.F.214')
         AND endereco.ds_estado = 'MATO GROSSO DO SUL')
     OR (sup_map.nk_supervisor IN ('B.F.80','B.F.1017','B.F.253')
         AND endereco.ds_estado = 'MATO GROSSO')
  )
ORDER BY clifor.cd_clifor, clifor.dt_ultaltecadastro DESC
"""


def fetch_portfolio() -> list[PortfolioRow]:
    schema = settings.erp_db_schema
    query = PORTFOLIO_QUERY.format(schema=schema)

    try:
        conn = get_erp_connection()
    except Exception as exc:
        raise ErpConfigError(f"Erro ao conectar no ERP: {exc}") from exc

    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = []
            for record in cur.fetchall():
                rows.append(PortfolioRow(
                    clifor=str(record[0] or "").strip(),
                    cnpj=str(record[1] or "").strip(),
                    client_name=str(record[2] or "").strip(),
                    seller_name=str(record[3] or "").strip(),
                    seller_name_normalized=normalize_name(record[3]),
                    supervisor_code=str(record[4] or "").strip(),
                    municipality=str(record[5] or "").strip(),
                    state=str(record[6] or "").strip(),
                ))
            return rows
    except Exception as exc:
        raise ErpQueryError(f"Erro ao consultar carteira: {exc}") from exc
    finally:
        conn.close()
