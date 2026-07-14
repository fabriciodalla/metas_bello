from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.allocations.models import GoalAllocation
from apps.allocations.services import ChildAllocationSpec, DistributeGoalService
from apps.catalog.models import ProductGroup
from apps.hierarchy.models import HierarchyNode

from .models import Cycle

User = get_user_model()


class CycleApiTests(APITestCase):
    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=7)
        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
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

        response = self.client.get(reverse("cycle-list"))

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_completeness_reports_stuck_allocation(self):
        response = self.client.get(reverse("cycle-completeness", kwargs={"pk": self.cycle.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["complete"])
        self.assertEqual(len(response.data["stuck_allocations"]), 1)

    def test_close_rejects_incomplete_cycle(self):
        response = self.client.post(reverse("cycle-close", kwargs={"pk": self.cycle.pk}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.cycle.refresh_from_db()
        self.assertEqual(self.cycle.status, Cycle.Status.ABERTO)

    def test_close_succeeds_when_complete(self):
        vendedor = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor", parent=self.gerente
        )
        DistributeGoalService.distribute(
            self.allocation,
            [
                ChildAllocationSpec(
                    owner_node_id=vendedor.id,
                    quantity_kg=100,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                )
            ],
            criado_por=self.user,
        )

        response = self.client.post(reverse("cycle-close", kwargs={"pk": self.cycle.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Cycle.Status.FECHADO)

    def test_distribution_overview_rejects_non_admin(self):
        response = self.client.get(reverse("cycle-distribution-overview", kwargs={"pk": self.cycle.pk}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_distribution_overview_lists_allocation_owners_for_admin(self):
        admin = User.objects.create_user(username="admin", password="x", is_admin=True)
        self.client.force_login(admin)

        response = self.client.get(reverse("cycle-distribution-overview", kwargs={"pk": self.cycle.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        entry = response.data[0]
        self.assertEqual(entry["owner_node_nome"], "Gerente")
        self.assertEqual(entry["owner_node_usernames"], ["gerente"])
        self.assertFalse(entry["distributed"])

    def test_export_rejects_non_admin(self):
        response = self.client.get(reverse("cycle-export", kwargs={"pk": self.cycle.pk}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_export_returns_csv_with_all_allocations(self):
        admin = User.objects.create_user(username="admin", password="x", is_admin=True)
        self.client.force_login(admin)

        response = self.client.get(reverse("cycle-export", kwargs={"pk": self.cycle.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        body = response.content.decode("utf-8")
        self.assertIn("Gerente", body)
        self.assertIn(str(self.allocation.quantity_kg), body)
