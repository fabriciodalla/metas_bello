from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import ExternalProductMapping, ProductGroup, ProductSubgroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import ExternalSalespersonMapping, HierarchyNode
from apps.sales_history.models import DistributionBaseline

from .models import GoalAllocation
from .services import (
    AllocationClosureError,
    AllocationScopeError,
    DistributionContextService,
    SplitGroupIntoSubgroupsService,
    SubgroupDistributionContextService,
    SubgroupSplitSpec,
)

User = get_user_model()


def _baseline(ano: int, mes: int, salesperson_name: str, subgroup_name: str, quantity: float) -> None:
    DistributionBaseline.objects.create(
        ano=ano,
        mes=mes,
        salesperson_name=salesperson_name,
        subgroup_name=subgroup_name,
        total_quantity=quantity,
    )


class SubgroupSupervisorContextTestsBase(TestCase):
    """Hierarquia/histórico compartilhados: um Coordenador Local com dois Supervisores, cada um
    com um Vendedor, vendendo dois subgrupos do mesmo grupo em proporção 75/25 tanto entre
    subgrupos (Linguiça/Salsicha) quanto entre Supervisores (A/B) — mesma proporção nos dois eixos
    de propósito, pra deixar as duas fórmulas fáceis de distinguir e conferir nos testes."""

    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.subgroup_linguica = ProductSubgroup.objects.create(nome="Linguiça", group=self.group)
        self.subgroup_salsicha = ProductSubgroup.objects.create(nome="Salsicha", group=self.group)
        ExternalProductMapping.objects.create(external_code="LINGUICA", subgroup=self.subgroup_linguica)
        ExternalProductMapping.objects.create(external_code="SALSICHA", subgroup=self.subgroup_salsicha)

        self.cycle = Cycle.objects.create(ano=2026, mes=1)

        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional", parent=self.gerente
        )
        self.local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local", parent=self.regional
        )
        self.supervisor_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor A", parent=self.local
        )
        self.supervisor_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor B", parent=self.local
        )
        vendedor_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor A", parent=self.supervisor_a
        )
        vendedor_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor B", parent=self.supervisor_b
        )
        ExternalSalespersonMapping.objects.create(external_name="VENDEDOR A", hierarchy_node=vendedor_a)
        ExternalSalespersonMapping.objects.create(external_name="VENDEDOR B", hierarchy_node=vendedor_b)

        # 12 meses planos (sem tendência). Por subgrupo (somando os dois Supervisores):
        # Linguiça = 225+75 = 300/mês, Salsicha = 75+25 = 100/mês -> 75/25 entre subgrupos.
        # Por Supervisor (somando os dois subgrupos): A = 225+75 = 300/mês, B = 75+25 = 100/mês
        # -> 75/25 entre Supervisores também, com histórico sempre do GRUPO inteiro (nunca só de
        # um subgrupo), como manda a Decisão 6.
        for mes in range(1, 13):
            _baseline(2025, mes, "VENDEDOR A", "LINGUICA", 225)
            _baseline(2025, mes, "VENDEDOR A", "SALSICHA", 75)
            _baseline(2025, mes, "VENDEDOR B", "LINGUICA", 75)
            _baseline(2025, mes, "VENDEDOR B", "SALSICHA", 25)


class SubgroupDistributionContextServiceTests(SubgroupSupervisorContextTestsBase):
    """Etapa 1: quebra da meta GROUP do Coordenador Local em subgrupos."""

    def test_suggests_split_weighted_by_subgroup_history_closing_exactly_with_parent(self):
        allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=1000,
            criado_por=User.objects.create_user(username="local1", password="x"),
        )

        contexts = SubgroupDistributionContextService.build(allocation)
        by_subgroup = {ctx.subgroup_id: ctx for ctx in contexts}

        self.assertEqual(set(by_subgroup), {self.subgroup_linguica.id, self.subgroup_salsicha.id})
        self.assertEqual(by_subgroup[self.subgroup_linguica.id].suggested_kg, 750)
        self.assertEqual(by_subgroup[self.subgroup_salsicha.id].suggested_kg, 250)
        self.assertEqual(
            by_subgroup[self.subgroup_linguica.id].suggested_kg
            + by_subgroup[self.subgroup_salsicha.id].suggested_kg,
            1000,
        )
        self.assertEqual(by_subgroup[self.subgroup_linguica.id].subgroup_nome, "Linguiça")
        self.assertAlmostEqual(by_subgroup[self.subgroup_linguica.id].historical_share_pct, 75.0)
        self.assertAlmostEqual(by_subgroup[self.subgroup_salsicha.id].historical_share_pct, 25.0)
        self.assertFalse(by_subgroup[self.subgroup_linguica.id].has_gap)

    def test_no_suggestion_when_no_history_for_any_subgroup(self):
        group_without_history = ProductGroup.objects.create(nome="Laticínios")
        subgroup_without_history = ProductSubgroup.objects.create(nome="Queijo", group=group_without_history)
        ExternalProductMapping.objects.create(external_code="QUEIJO", subgroup=subgroup_without_history)

        allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local,
            granularity=GoalAllocation.Granularity.GROUP,
            group=group_without_history,
            quantity_kg=500,
            criado_por=User.objects.create_user(username="local2", password="x"),
        )

        contexts = SubgroupDistributionContextService.build(allocation)

        self.assertEqual(len(contexts), 1)
        self.assertIsNone(contexts[0].suggested_kg)

    def test_returns_empty_when_allocation_has_no_group(self):
        subgroup_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local,
            granularity=GoalAllocation.Granularity.SUBGROUP,
            subgroup=self.subgroup_linguica,
            quantity_kg=1000,
            criado_por=User.objects.create_user(username="local3", password="x"),
        )

        self.assertEqual(SubgroupDistributionContextService.build(subgroup_allocation), [])


class SplitGroupIntoSubgroupsServiceTests(SubgroupSupervisorContextTestsBase):
    """Tela "Distribuir Produtos": persiste a quebra da meta GROUP do Coordenador Local em metas
    SUBGROUP, permanecendo dona do mesmo nó Local."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="local4", password="x", hierarchy_node=self.local)
        self.allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=1000,
            criado_por=self.user,
        )

    def test_persists_children_owned_by_same_node_and_closes_exactly(self):
        specs = [
            SubgroupSplitSpec(subgroup_id=self.subgroup_linguica.id, quantity_kg=750),
            SubgroupSplitSpec(subgroup_id=self.subgroup_salsicha.id, quantity_kg=250),
        ]

        created = SplitGroupIntoSubgroupsService.split(self.allocation, specs, criado_por=self.user)
        by_subgroup = {c.subgroup_id: c for c in created}

        self.assertEqual(len(created), 2)
        self.assertTrue(all(c.owner_node_id == self.local.id for c in created))
        self.assertTrue(all(c.granularity == GoalAllocation.Granularity.SUBGROUP for c in created))
        self.assertTrue(all(c.parent_allocation_id == self.allocation.id for c in created))
        self.assertEqual(by_subgroup[self.subgroup_linguica.id].quantity_kg, 750)
        self.assertEqual(by_subgroup[self.subgroup_salsicha.id].quantity_kg, 250)

        self.allocation.refresh_from_db()
        self.assertTrue(self.allocation.distributed)

    def test_rejects_when_sum_does_not_close_with_parent(self):
        specs = [SubgroupSplitSpec(subgroup_id=self.subgroup_linguica.id, quantity_kg=999)]

        with self.assertRaises(AllocationClosureError):
            SplitGroupIntoSubgroupsService.split(self.allocation, specs, criado_por=self.user)

    def test_rejects_subgroup_not_belonging_to_allocation_group(self):
        other_group = ProductGroup.objects.create(nome="Laticínios")
        other_subgroup = ProductSubgroup.objects.create(nome="Queijo", group=other_group)
        specs = [SubgroupSplitSpec(subgroup_id=other_subgroup.id, quantity_kg=1000)]

        with self.assertRaises(AllocationScopeError):
            SplitGroupIntoSubgroupsService.split(self.allocation, specs, criado_por=self.user)

    def test_rejects_when_owner_level_is_not_local(self):
        regional_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.regional,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=1000,
            criado_por=User.objects.create_user(
                username="regional5", password="x", hierarchy_node=self.regional
            ),
        )
        specs = [SubgroupSplitSpec(subgroup_id=self.subgroup_linguica.id, quantity_kg=1000)]

        with self.assertRaises(AllocationScopeError):
            SplitGroupIntoSubgroupsService.split(
                regional_allocation, specs, criado_por=regional_allocation.criado_por
            )

    def test_rejects_when_caller_does_not_own_the_allocation(self):
        other_user = User.objects.create_user(username="other", password="x")
        specs = [SubgroupSplitSpec(subgroup_id=self.subgroup_linguica.id, quantity_kg=1000)]

        with self.assertRaises(AllocationScopeError):
            SplitGroupIntoSubgroupsService.split(self.allocation, specs, criado_por=other_user)


class DistributionContextServiceOnSubgroupTests(SubgroupSupervisorContextTestsBase):
    """A tela "Meta Supervisor" chama `DistributionContextService.build()` numa alocação SUBGROUP
    já persistida (dona = Local) — mesmo peso por Supervisor que já funciona pra GROUP, resolvendo
    o grupo via `subgroup.group_id` em vez de `allocation.group_id`."""

    def test_suggests_split_weighted_by_full_group_history_not_subgroup(self):
        subgroup_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local,
            granularity=GoalAllocation.Granularity.SUBGROUP,
            subgroup=self.subgroup_salsicha,
            quantity_kg=400,
            criado_por=User.objects.create_user(username="local6", password="x"),
        )

        contexts = DistributionContextService.build(subgroup_allocation)
        by_node = {ctx.owner_node_id: ctx for ctx in contexts}

        self.assertEqual(set(by_node), {self.supervisor_a.id, self.supervisor_b.id})
        self.assertEqual(by_node[self.supervisor_a.id].suggested_kg, 300)
        self.assertEqual(by_node[self.supervisor_b.id].suggested_kg, 100)


class SubgroupSupervisorContextApiTests(APITestCase):
    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.subgroup = ProductSubgroup.objects.create(nome="Linguiça", group=self.group)
        self.cycle = Cycle.objects.create(ano=2026, mes=1)
        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional", parent=self.gerente
        )
        self.local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local", parent=self.regional
        )
        self.user = User.objects.create_user(username="local", password="x", hierarchy_node=self.local)
        self.allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=1000,
            criado_por=self.user,
        )
        self.client.force_login(self.user)

    def test_subgroup_distribution_context_rejects_non_owner(self):
        admin_user = User.objects.create_user(username="admin", password="x", is_admin=True)
        self.client.force_login(admin_user)

        response = self.client.get(
            reverse("goal-allocation-subgroup-distribution-context", args=[self.allocation.id])
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_subgroup_distribution_context_returns_context_per_subgroup(self):
        response = self.client.get(
            reverse("goal-allocation-subgroup-distribution-context", args=[self.allocation.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["subgroup_id"], self.subgroup.id)
        self.assertIsNone(response.data[0]["suggested_kg"])

    def test_split_subgroups_persists_and_closes_exactly(self):
        response = self.client.post(
            reverse("goal-allocation-split-subgroups", args=[self.allocation.id]),
            {"subgroups": [{"subgroup_id": self.subgroup.id, "quantity_kg": 1000}]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["owner_node"], self.local.id)
        self.assertEqual(response.data[0]["granularity"], "SUBGROUP")

    def test_split_subgroups_rejects_when_it_does_not_close_exactly(self):
        response = self.client.post(
            reverse("goal-allocation-split-subgroups", args=[self.allocation.id]),
            {"subgroups": [{"subgroup_id": self.subgroup.id, "quantity_kg": 1}]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
