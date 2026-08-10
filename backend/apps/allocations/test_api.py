from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import ProductGroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import HierarchyNode

from .models import GoalAllocation

User = get_user_model()


class GoalAllocationApiTests(APITestCase):
    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=7)
        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional A", parent=self.gerente
        )
        self.regional_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional B", parent=self.gerente
        )
        self.user = User.objects.create_user(username="gerente", password="x", hierarchy_node=self.gerente)
        self.allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=100,
            criado_por=self.user,
        )
        self.client.force_login(self.user)

    def test_requires_authentication(self):
        self.client.logout()

        response = self.client.get(reverse("goal-allocation-list"))

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_retrieve_outside_scope_returns_404(self):
        other_node = HierarchyNode.objects.create(level=HierarchyNode.Level.REGIONAL, nome="Outro")
        other_user = User.objects.create_user(username="outro", password="x", hierarchy_node=other_node)
        other_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=other_node,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=10,
            criado_por=other_user,
        )

        response = self.client.get(reverse("goal-allocation-detail", kwargs={"pk": other_allocation.pk}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_distribute_rejects_when_user_does_not_own_parent_via_api(self):
        # regional_a é descendente de gerente, então a alocação é *visível* para self.user
        # (owner_node=gerente) via visible_to — mas ele não é o dono direto dela. Isso exercita
        # o AllocationScopeError do service através da view (visível != dono), diferente do 404
        # de test_retrieve_outside_scope_returns_404 (fora do escopo, nem visível).
        local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local A1", parent=self.regional_a
        )
        regional_a_user = User.objects.create_user(
            username="regional_a", password="x", hierarchy_node=self.regional_a
        )
        regional_a_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.regional_a,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=60,
            criado_por=regional_a_user,
        )

        payload = {
            "children": [
                {
                    "owner_node_id": local.id,
                    "quantity_kg": 60,
                    "granularity": "GROUP",
                    "group_id": self.group.id,
                },
            ]
        }

        response = self.client.post(
            reverse("goal-allocation-distribute", kwargs={"pk": regional_a_allocation.pk}),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        regional_a_allocation.refresh_from_db()
        self.assertFalse(regional_a_allocation.distributed)

    def test_distribute_succeeds_and_returns_created_children(self):
        payload = {
            "children": [
                {
                    "owner_node_id": self.regional_a.id,
                    "quantity_kg": 60,
                    "granularity": "GROUP",
                    "group_id": self.group.id,
                },
                {
                    "owner_node_id": self.regional_b.id,
                    "quantity_kg": 40,
                    "granularity": "GROUP",
                    "group_id": self.group.id,
                },
            ]
        }

        response = self.client.post(
            reverse("goal-allocation-distribute", kwargs={"pk": self.allocation.pk}), payload, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 2)
        self.allocation.refresh_from_db()
        self.assertTrue(self.allocation.distributed)

    def test_distribute_rejects_mismatched_sum(self):
        payload = {
            "children": [
                {
                    "owner_node_id": self.regional_a.id,
                    "quantity_kg": 60,
                    "granularity": "GROUP",
                    "group_id": self.group.id,
                },
                {
                    "owner_node_id": self.regional_b.id,
                    "quantity_kg": 30,
                    "granularity": "GROUP",
                    "group_id": self.group.id,
                },
            ]
        }

        response = self.client.post(
            reverse("goal-allocation-distribute", kwargs={"pk": self.allocation.pk}), payload, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reopen_via_api_deletes_children_and_resets_distributed(self):
        distribute_payload = {
            "children": [
                {
                    "owner_node_id": self.regional_a.id,
                    "quantity_kg": 60,
                    "granularity": "GROUP",
                    "group_id": self.group.id,
                },
                {
                    "owner_node_id": self.regional_b.id,
                    "quantity_kg": 40,
                    "granularity": "GROUP",
                    "group_id": self.group.id,
                },
            ]
        }
        self.client.post(
            reverse("goal-allocation-distribute", kwargs={"pk": self.allocation.pk}),
            distribute_payload,
            format="json",
        )
        child_ids = list(
            GoalAllocation.objects.filter(parent_allocation=self.allocation).values_list("id", flat=True)
        )
        self.assertEqual(len(child_ids), 2)

        response = self.client.post(reverse("goal-allocation-reopen", kwargs={"pk": self.allocation.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["distributed"])
        self.allocation.refresh_from_db()
        self.assertFalse(self.allocation.distributed)
        self.assertFalse(GoalAllocation.objects.filter(id__in=child_ids).exists())

    def test_reopen_via_api_rejects_when_not_yet_distributed(self):
        response = self.client.post(reverse("goal-allocation-reopen", kwargs={"pk": self.allocation.pk}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_shows_allocations_in_own_branch(self):
        other_node = HierarchyNode.objects.create(level=HierarchyNode.Level.REGIONAL, nome="Outro")
        other_user = User.objects.create_user(username="outro", password="x", hierarchy_node=other_node)
        GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=other_node,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=10,
            criado_por=other_user,
        )

        response = self.client.get(reverse("goal-allocation-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {self.allocation.id})
