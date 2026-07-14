import datetime
from collections import defaultdict
from decimal import Decimal

from django.db import connections, transaction

from .models import AccumulatedSale, ClientPortfolioSnapshot, DistributionBaseline
from .queries import ACUMULADO_SQL, CARTEIRA_SQL


def _fetch_as_dicts(alias: str, sql: str, params: list | None = None) -> list[dict]:
    with connections[alias].cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def first_day_n_months_ago(today: datetime.date, months_back: int) -> datetime.date:
    """Compartilhado entre o comando `sync_sales_history` e o endpoint de sync do Administrador,
    pra não duplicar a aritmética de janela de meses (H2, 12 meses por padrão)."""
    year = today.year
    month = today.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return datetime.date(year, month, 1)


class SalesHistorySyncService:
    """Roda as duas consultas no Postgres externo (somente leitura) e grava o resultado nas
    tabelas locais da aplicação. Nenhuma fórmula de negócio roda aqui — só espelha os dados.
    """

    @staticmethod
    def sync_accumulated(min_date: datetime.date) -> int:
        rows = _fetch_as_dicts("sales_history", ACUMULADO_SQL, [min_date])

        with transaction.atomic():
            AccumulatedSale.objects.filter(sale_date__gte=min_date).delete()
            AccumulatedSale.objects.bulk_create(
                AccumulatedSale(
                    nk_supervisor=row["nk_supervisor"],
                    nk_vendedor=row["nk_vendedor"],
                    salesperson_name=row["nome_vendedor"],
                    client_code=row["clifor"],
                    cnpj=row["cnpj"] or "",
                    client_name=row["nome_cliente"] or "",
                    sale_date=row["dt_emissao"],
                    subgroup_name=row["ds_subgrupo"],
                    total_quantity=row["total_ps_atendido"],
                    total_value=row["total_vl_movtocontabil"],
                )
                for row in rows
            )

        return len(rows)

    @staticmethod
    def sync_portfolio() -> int:
        rows = _fetch_as_dicts("sales_history", CARTEIRA_SQL)

        with transaction.atomic():
            ClientPortfolioSnapshot.objects.all().delete()
            ClientPortfolioSnapshot.objects.bulk_create(
                ClientPortfolioSnapshot(
                    client_code=row["clifor"],
                    cnpj=row["cnpj"] or "",
                    client_name=row["nome_cliente"],
                    salesperson_name=row["nome_vendedor"],
                    nk_supervisor=row["nk_supervisor"],
                    municipio=row["municipio"] or "",
                    estado=row["estado"] or "",
                    registered_at=row["cadastro"],
                    last_changed_at=row["alterado"],
                )
                for row in rows
            )

        return len(rows)


class DistributionBaselineService:
    """Constrói a base de cálculo de distribuição de metas a partir das duas tabelas locais.

    Reatribui cada linha do acumulado ao vendedor ATUAL da carteira do cliente (join por
    `client_code`, comum às duas tabelas) — não importa quem historicamente vendeu, importa
    quanto o cliente comprou, e esse total conta para quem hoje é responsável por ele. Clientes do
    acumulado sem entrada na carteira atual ficam de fora (sem vendedor vigente pra atribuir).
    """

    @staticmethod
    @transaction.atomic
    def rebuild() -> int:
        current_salesperson_by_client = dict(
            ClientPortfolioSnapshot.objects.values_list("client_code", "salesperson_name")
        )

        totals: dict[tuple[int, int, str, str], Decimal] = defaultdict(Decimal)
        rows = AccumulatedSale.objects.values_list(
            "sale_date", "client_code", "subgroup_name", "total_quantity"
        )
        for sale_date, client_code, subgroup_name, quantity in rows:
            salesperson_name = current_salesperson_by_client.get(client_code)
            if salesperson_name is None:
                continue
            key = (sale_date.year, sale_date.month, salesperson_name, subgroup_name)
            totals[key] += quantity

        DistributionBaseline.objects.all().delete()
        DistributionBaseline.objects.bulk_create(
            DistributionBaseline(
                ano=ano,
                mes=mes,
                salesperson_name=salesperson_name,
                subgroup_name=subgroup_name,
                total_quantity=total_quantity,
            )
            for (ano, mes, salesperson_name, subgroup_name), total_quantity in totals.items()
        )

        return len(totals)
