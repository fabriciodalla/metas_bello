from django.core.management.base import BaseCommand

from apps.sales_history.services import DistributionBaselineService


class Command(BaseCommand):
    help = (
        "Reconstrói a base de cálculo de distribuição de metas a partir de AccumulatedSale + "
        "ClientPortfolioSnapshot já sincronizados localmente — não consulta o Postgres externo. "
        "Útil para recalcular sem esperar o próximo sync mensal."
    )

    def handle(self, *args, **options):
        count = DistributionBaselineService.rebuild()
        self.stdout.write(self.style.SUCCESS(f"Base de distribuição reconstruída: {count} linha(s)."))
