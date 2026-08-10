from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import ExternalProductMapping, ProductGroup, ProductSubgroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import HierarchyNode
from apps.sales_history.models import DistributionBaseline

from .models import GoalAllocation
from .services import (
    AllocationScopeError,
    CreateRootAllocationError,
    CreateRootAllocationService,
    GoalSuggestionService,
    previous_month,
)

User = get_user_model()


class PreviousMonthTests(TestCase):
    def test_regular_month_just_decrements(self):
        self.assertEqual(previous_month(2026, 7), (2026, 6))

    def test_january_wraps_to_december_of_previous_year(self):
        self.assertEqual(previous_month(2026, 1), (2025, 12))


def _seed_baseline(group: ProductGroup, monthly_values: list[tuple[int, int, float]]) -> None:
    """Cria subgrupo + ExternalProductMapping + DistributionBaseline pra um grupo, uma linha por
    mês — `group_history` (P1) soma por subgrupo, não aceita mapeamento direto no grupo (mesma
    forma da curadoria real: sempre subgroup_name -> ProductSubgroup)."""
    subgroup, _ = ProductSubgroup.objects.get_or_create(nome=f"Subgrupo {group.nome}", group=group)
    ExternalProductMapping.objects.get_or_create(
        external_code=f"ERP-{group.nome}", defaults={"subgroup": subgroup}
    )
    for ano, mes, quantity in monthly_values:
        DistributionBaseline.objects.create(
            ano=ano,
            mes=mes,
            salesperson_name="Fulano",
            subgroup_name=f"ERP-{group.nome}",
            total_quantity=quantity,
        )


class GoalSuggestionServiceTests(TestCase):
    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.other_group = ProductGroup.objects.create(nome="Frangos", ativo=False)
        self.cycle = Cycle.objects.create(ano=2026, mes=7)

        # Janela de 12 meses terminando em 06/2026 (mês anterior ao ciclo) — série linear limpa
        # (sem ruído sazonal) pra deixar o resultado previsível no teste.
        months = []
        ano, mes = 2025, 7
        for i in range(12):
            months.append((ano, mes, 100 + 10 * i))
            mes += 1
            if mes > 12:
                mes = 1
                ano += 1
        _seed_baseline(self.group, months)

    def test_suggests_only_active_groups(self):
        result = GoalSuggestionService.suggest_for_cycle(self.cycle)

        self.assertIn(self.group.id, result)
        self.assertNotIn(self.other_group.id, result)

    def test_projects_next_month_from_trend_and_seasonality(self):
        result = GoalSuggestionService.suggest_for_cycle(self.cycle)

        suggestion = result[self.group.id]
        # valores 100..210 (posições 1..12) -> intercepto 90, inclinação 10, projeção pos.13 = 220
        self.assertEqual(suggestion.suggested_kg, 220)
        self.assertFalse(suggestion.has_gap)
        self.assertEqual(suggestion.same_month_last_year_kg, 100.0)  # primeiro ponto da janela

    def test_flags_gap_when_a_month_has_no_baseline_data(self):
        DistributionBaseline.objects.filter(ano=2025, mes=7).delete()

        result = GoalSuggestionService.suggest_for_cycle(self.cycle)

        self.assertTrue(result[self.group.id].has_gap)


class CreateRootAllocationServiceTests(TestCase):
    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=7)
        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.user = User.objects.create_user(username="gerente", password="x", hierarchy_node=self.gerente)

    def test_creates_root_allocation_without_parent(self):
        allocation = CreateRootAllocationService.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            quantity_kg=1200,
            criado_por=self.user,
            group_id=self.group.id,
        )

        self.assertIsNone(allocation.parent_allocation_id)
        self.assertEqual(allocation.quantity_kg, 1200)

    def test_rejects_when_user_does_not_own_the_node(self):
        other_user = User.objects.create_user(username="outro", password="x")

        with self.assertRaises(AllocationScopeError):
            CreateRootAllocationService.create(
                cycle=self.cycle,
                owner_node=self.gerente,
                granularity=GoalAllocation.Granularity.GROUP,
                quantity_kg=1200,
                criado_por=other_user,
                group_id=self.group.id,
            )

    def test_rejects_non_gerente_level(self):
        local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local", parent=self.gerente
        )
        local_user = User.objects.create_user(username="local", password="x", hierarchy_node=local)

        with self.assertRaises(AllocationScopeError):
            CreateRootAllocationService.create(
                cycle=self.cycle,
                owner_node=local,
                granularity=GoalAllocation.Granularity.GROUP,
                quantity_kg=1200,
                criado_por=local_user,
                group_id=self.group.id,
            )

    def test_rejects_duplicate_root_for_same_group_and_cycle(self):
        CreateRootAllocationService.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            quantity_kg=1200,
            criado_por=self.user,
            group_id=self.group.id,
        )

        with self.assertRaises(CreateRootAllocationError):
            CreateRootAllocationService.create(
                cycle=self.cycle,
                owner_node=self.gerente,
                granularity=GoalAllocation.Granularity.GROUP,
                quantity_kg=999,
                criado_por=self.user,
                group_id=self.group.id,
            )


class GoalSuggestionApiTests(APITestCase):
    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=7)
        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.user = User.objects.create_user(username="gerente", password="x", hierarchy_node=self.gerente)
        self.client.force_login(self.user)

    def test_suggestions_requires_cycle_and_owner_node_params(self):
        response = self.client.get(reverse("goal-allocation-suggestions"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suggestions_rejects_node_outside_scope(self):
        other_node = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Outro")

        response = self.client.get(
            reverse("goal-allocation-suggestions"),
            {"cycle": self.cycle.id, "owner_node": other_node.id},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_suggestions_returns_breakdown_per_active_group(self):
        response = self.client.get(
            reverse("goal-allocation-suggestions"),
            {"cycle": self.cycle.id, "owner_node": self.gerente.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["group_id"] for item in response.data}
        self.assertIn(self.group.id, ids)
        row = next(item for item in response.data if item["group_id"] == self.group.id)
        self.assertFalse(row["already_created"])
        self.assertIn("history", row)
        self.assertIn("same_month_last_year_kg", row)

    def test_root_creates_allocation_and_marks_suggestion_as_already_created(self):
        payload = {
            "cycle_id": self.cycle.id,
            "owner_node_id": self.gerente.id,
            "granularity": "GROUP",
            "group_id": self.group.id,
            "quantity_kg": 1500,
        }

        response = self.client.post(reverse("goal-allocation-root"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GoalAllocation.objects.get(id=response.data["id"]).quantity_kg, 1500)

        suggestions_response = self.client.get(
            reverse("goal-allocation-suggestions"),
            {"cycle": self.cycle.id, "owner_node": self.gerente.id},
        )
        row = next(item for item in suggestions_response.data if item["group_id"] == self.group.id)
        self.assertTrue(row["already_created"])

    def test_root_rejects_duplicate(self):
        payload = {
            "cycle_id": self.cycle.id,
            "owner_node_id": self.gerente.id,
            "granularity": "GROUP",
            "group_id": self.group.id,
            "quantity_kg": 1500,
        }
        self.client.post(reverse("goal-allocation-root"), payload, format="json")

        response = self.client.post(reverse("goal-allocation-root"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
