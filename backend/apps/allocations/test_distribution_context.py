from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import ExternalProductMapping, Product, ProductGroup, ProductSubgroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import ExternalSalespersonMapping, HierarchyNode
from apps.sales_history.models import DistributionBaseline

from .models import GoalAllocation
from .services import DistributionContextService

User = get_user_model()


def _baseline(ano: int, mes: int, salesperson_name: str, subgroup_name: str, quantity: float) -> None:
    DistributionBaseline.objects.create(
        ano=ano,
        mes=mes,
        salesperson_name=salesperson_name,
        subgroup_name=subgroup_name,
        total_quantity=quantity,
    )


class DistributionContextServiceTests(TestCase):
    """Contexto histórico por filho direto (histórico, comparativos, participação e, quando o
    nível tem AUTO ligada, meta sugerida) — nunca inventa fórmula nova, só orquestra P1-P4."""

    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.subgroup = ProductSubgroup.objects.create(nome="Linguiça", group=self.group)
        ExternalProductMapping.objects.create(external_code="LINGUICA", subgroup=self.subgroup)

        self.cycle = Cycle.objects.create(ano=2026, mes=1)

        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional A", parent=self.gerente
        )
        self.regional_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional B", parent=self.gerente
        )
        vendedor_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor A", parent=self.regional_a
        )
        vendedor_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor B", parent=self.regional_b
        )
        ExternalSalespersonMapping.objects.create(external_name="VENDEDOR A", hierarchy_node=vendedor_a)
        ExternalSalespersonMapping.objects.create(external_name="VENDEDOR B", hierarchy_node=vendedor_b)

        # Janela de 12 meses terminando em 12/2025 (mês anterior ao ciclo 01/2026). Regional A
        # vende o triplo de Regional B, plano (sem tendência) — participação previsível: 75/25.
        for mes in range(1, 13):
            _baseline(2025, mes, "VENDEDOR A", "LINGUICA", 300)
            _baseline(2025, mes, "VENDEDOR B", "LINGUICA", 100)

    def test_gerente_level_prefills_suggested_kg_closing_exactly_with_parent(self):
        """Gerente→Regional passou a ter modo AUTO ligado (2026-07-22, ver Decisão 6): mesma
        fórmula tendência+sazonalidade de P2-P4, pré-preenchendo uma sugestão editável que fecha
        exato com o total do Gerente."""
        allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=1000,
            criado_por=User.objects.create_user(username="g", password="x"),
        )

        contexts = DistributionContextService.build(allocation)
        by_node = {ctx.owner_node_id: ctx for ctx in contexts}

        self.assertEqual(set(by_node), {self.regional_a.id, self.regional_b.id})
        self.assertEqual(by_node[self.regional_a.id].suggested_kg, 750)
        self.assertEqual(by_node[self.regional_b.id].suggested_kg, 250)
        self.assertEqual(
            by_node[self.regional_a.id].suggested_kg + by_node[self.regional_b.id].suggested_kg, 1000
        )
        self.assertEqual(by_node[self.regional_a.id].same_month_last_year_kg, 300.0)
        self.assertEqual(by_node[self.regional_a.id].last_3_months_avg_kg, 300.0)
        self.assertAlmostEqual(by_node[self.regional_a.id].historical_share_pct, 75.0)
        self.assertAlmostEqual(by_node[self.regional_b.id].historical_share_pct, 25.0)
        self.assertFalse(by_node[self.regional_a.id].has_gap)

    def test_gerente_level_has_no_suggested_kg_when_no_target_has_history(self):
        """Sem histórico curado pra nenhum alvo (ExternalSalespersonMapping vazio, ver O3), a
        proporção soma zero — a fórmula não crasha, só degrada pra "sem sugestão"."""
        group_without_history = ProductGroup.objects.create(nome="Laticínios")
        subgroup_without_history = ProductSubgroup.objects.create(nome="Queijo", group=group_without_history)
        ExternalProductMapping.objects.create(external_code="QUEIJO", subgroup=subgroup_without_history)

        allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=group_without_history,
            quantity_kg=500,
            criado_por=User.objects.create_user(username="g4", password="x"),
        )

        contexts = DistributionContextService.build(allocation)
        by_node = {ctx.owner_node_id: ctx for ctx in contexts}

        self.assertIsNone(by_node[self.regional_a.id].suggested_kg)
        self.assertIsNone(by_node[self.regional_b.id].suggested_kg)

    def test_regional_level_prefills_suggested_kg_closing_exactly_with_parent(self):
        """Regional→Local já tem fórmula AUTO aprovada (P2) — aqui ela pré-preenche a sugestão,
        fechando exato com o total do pai (mesma garantia do fechamento hierárquico)."""
        local_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local A1", parent=self.regional_a
        )
        # Reaproveita o vendedor A já mapeado, só reparentando pra baixo de local_a pra simular
        # Regional A distribuindo pro seu único Local. `.save()` (não `.update()`) é obrigatório
        # aqui — é o que mantém a HierarchyClosure em dia (ScopeResolver.descendant_ids depende
        # dela, não é derivada on-the-fly do `parent`).
        vendedor_a_node = HierarchyNode.objects.get(nome="Vendedor A")
        vendedor_a_node.parent = local_a
        vendedor_a_node.save()

        allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.regional_a,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=900,
            criado_por=User.objects.create_user(username="r", password="x"),
        )

        contexts = DistributionContextService.build(allocation)

        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0].owner_node_id, local_a.id)
        self.assertEqual(contexts[0].suggested_kg, 900)  # único filho, recebe o total inteiro

    def test_flags_gap_when_a_month_has_no_baseline_data(self):
        DistributionBaseline.objects.filter(ano=2025, mes=1, salesperson_name="VENDEDOR A").delete()
        allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=1000,
            criado_por=User.objects.create_user(username="g2", password="x"),
        )

        contexts = DistributionContextService.build(allocation)
        by_node = {ctx.owner_node_id: ctx for ctx in contexts}

        self.assertTrue(by_node[self.regional_a.id].has_gap)

    def test_resolves_group_from_subgroup_when_allocation_is_subgroup_granularity(self):
        """Generalização usada pela tela "Meta Supervisor": uma alocação SUBGROUP (não só GROUP)
        também gera contexto/sugestão, resolvendo o grupo via `subgroup.group_id`."""
        subgroup_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.SUBGROUP,
            subgroup=self.subgroup,
            quantity_kg=1000,
            criado_por=User.objects.create_user(username="g3", password="x"),
        )

        contexts = DistributionContextService.build(subgroup_allocation)
        by_node = {ctx.owner_node_id: ctx for ctx in contexts}

        self.assertEqual(set(by_node), {self.regional_a.id, self.regional_b.id})
        self.assertEqual(by_node[self.regional_a.id].suggested_kg, 750)
        self.assertEqual(by_node[self.regional_b.id].suggested_kg, 250)

    def test_returns_empty_when_allocation_has_neither_group_nor_subgroup(self):
        product_subgroup = ProductSubgroup.objects.create(nome="Copa", group=self.group)
        product = Product.objects.create(nome="Copa 500g", subgroup=product_subgroup)
        product_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.PRODUCT,
            product=product,
            quantity_kg=1000,
            criado_por=User.objects.create_user(username="g4b", password="x"),
        )

        self.assertEqual(DistributionContextService.build(product_allocation), [])


class DistributionContextApiTests(APITestCase):
    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=1)
        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional", parent=self.gerente
        )
        self.user = User.objects.create_user(username="gerente", password="x", hierarchy_node=self.gerente)
        self.allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=1000,
            criado_por=self.user,
        )
        self.client.force_login(self.user)

    def test_rejects_when_user_does_not_own_the_allocation(self):
        # Admin vê a alocação (is_admin ignora o filtro de escopo de `visible_to`), mas não a
        # possui — mesma semântica de posse já usada por `distribute()`/`reopen()`.
        admin_user = User.objects.create_user(username="admin", password="x", is_admin=True)
        self.client.force_login(admin_user)

        response = self.client.get(reverse("goal-allocation-distribution-context", args=[self.allocation.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_context_per_direct_child(self):
        response = self.client.get(reverse("goal-allocation-distribution-context", args=[self.allocation.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["owner_node_id"], self.regional.id)
        self.assertIsNone(response.data[0]["suggested_kg"])
