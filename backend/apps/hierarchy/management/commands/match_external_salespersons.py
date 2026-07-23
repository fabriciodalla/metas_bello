from django.core.management.base import BaseCommand
from django.db import transaction

from apps.hierarchy.models import ExternalSalespersonMapping, HierarchyNode
from apps.sales_history.models import DistributionBaseline


class Command(BaseCommand):
    """Liga HierarchyNode (VENDEDOR) a ExternalSalespersonMapping por igualdade EXATA de nome
    contra DistributionBaseline.salesperson_name — não normaliza, não aproxima (Decisão 9,
    revisão 2026-07-22: o usuário confirmou que os nomes cadastrados são idênticos aos do ERP
    nesta base; ver docs/decisions.md). Idempotente: só cria o que ainda não existe."""

    help = "Cria ExternalSalespersonMapping por igualdade exata de nome (Vendedor x DistributionBaseline)."

    @transaction.atomic
    def handle(self, *args, **options):
        already_mapped_node_ids = set(
            ExternalSalespersonMapping.objects.values_list("hierarchy_node_id", flat=True)
        )
        already_mapped_names = set(ExternalSalespersonMapping.objects.values_list("external_name", flat=True))

        candidate_nodes = HierarchyNode.objects.filter(level=HierarchyNode.Level.VENDEDOR).exclude(
            id__in=already_mapped_node_ids
        )
        baseline_names = set(
            name
            for name in DistributionBaseline.objects.values_list("salesperson_name", flat=True).distinct()
            if name
        )
        available_names = baseline_names - already_mapped_names

        created = []
        unmatched = []
        for node in candidate_nodes:
            if node.nome in available_names:
                ExternalSalespersonMapping.objects.create(external_name=node.nome, hierarchy_node=node)
                created.append(node.nome)
            else:
                unmatched.append(node.nome)

        self.stdout.write(self.style.SUCCESS(f"Mapeamentos criados: {len(created)}"))
        for name in sorted(created):
            self.stdout.write(f"  + {name}")

        if unmatched:
            self.stdout.write(
                self.style.WARNING(f"\nSem correspondência exata (curadoria manual): {len(unmatched)}")
            )
            for name in sorted(unmatched):
                self.stdout.write(f"  ? {name}")
