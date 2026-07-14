from datetime import date

from django.core.management.base import BaseCommand

from apps.sales_history.services import DistributionBaselineService, SalesHistorySyncService


def first_day_n_months_ago(today: date, months_back: int) -> date:
    year = today.year
    month = today.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


class Command(BaseCommand):
    help = (
        "Sincroniza acumulado de vendas e carteira de clientes do Postgres externo (somente "
        "leitura) para as tabelas locais da aplicação."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--months",
            type=int,
            default=12,
            help=(
                "Quantos meses (incluindo o atual) de acumulado sincronizar. Default: 12 — janela "
                "confirmada com o usuário (H2 resolvida) para a decomposição tendência+sazonalidade "
                "de P1-P4, ver docs/decisions.md (Decisão 6)."
            ),
        )

    def handle(self, *args, **options):
        min_date = first_day_n_months_ago(date.today(), options["months"] - 1)

        accumulated_count = SalesHistorySyncService.sync_accumulated(min_date)
        self.stdout.write(f"Acumulado: {accumulated_count} linha(s) sincronizada(s) desde {min_date}.")

        portfolio_count = SalesHistorySyncService.sync_portfolio()
        self.stdout.write(f"Carteira: {portfolio_count} cliente(s) sincronizado(s).")

        baseline_count = DistributionBaselineService.rebuild()
        self.stdout.write(f"Base de distribuição: {baseline_count} linha(s) recalculada(s).")
