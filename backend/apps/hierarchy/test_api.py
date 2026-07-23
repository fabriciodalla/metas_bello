from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.allocations.models import GoalAllocation
from apps.allocations.services import ChildAllocationSpec, DistributeGoalService
from apps.catalog.models import ProductGroup
from apps.cycles.models import Cycle

from .models import FeristaCoverage, HierarchyNode

User = get_user_model()


class HierarchyNodeApiTests(APITestCase):
    def setUp(self):
        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional A", parent=self.gerente
        )
        self.regional_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional B", parent=self.gerente
        )
        self.user_a = User.objects.create_user(
            username="user_a", password="x", hierarchy_node=self.regional_a
        )

    def test_requires_authentication(self):
        response = self.client.get(reverse("hierarchy-node-list"))

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_lists_only_own_branch(self):
        self.client.force_login(self.user_a)

        response = self.client.get(reverse("hierarchy-node-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {self.regional_a.id})
        self.assertNotIn(self.regional_b.id, ids)


class HierarchyNodeAdminApiTests(APITestCase):
    """CRUD de hierarquia pela SPA (Decisão 4 revista) — antes só existia via Django Admin,
    ver test_admin.py para os testes equivalentes daquele caminho."""

    def setUp(self):
        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional", parent=self.gerente
        )
        self.admin = User.objects.create_user(username="admin", password="x", is_admin=True)
        self.plain_user = User.objects.create_user(
            username="user", password="x", hierarchy_node=self.regional
        )

    def test_non_admin_cannot_create_node(self):
        self.client.force_login(self.plain_user)

        response = self.client.post(
            reverse("hierarchy-node-list"),
            {"level": HierarchyNode.Level.LOCAL, "nome": "Local X", "parent": self.regional.id},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_node_with_valid_parent_level(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("hierarchy-node-list"),
            {"level": HierarchyNode.Level.LOCAL, "nome": "Local X", "parent": self.regional.id},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(HierarchyNode.objects.filter(nome="Local X", parent=self.regional).exists())

    def test_rejects_parent_of_wrong_level(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("hierarchy-node-list"),
            {"level": HierarchyNode.Level.SUPERVISOR, "nome": "Supervisor X", "parent": self.regional.id},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_gerente_with_parent(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("hierarchy-node-list"),
            {"level": HierarchyNode.Level.GERENTE, "nome": "Outro Gerente", "parent": self.regional.id},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_node_as_its_own_parent(self):
        """A API (diferente do Django Admin) não chamava `full_clean()` — um nó podia virar pai
        de si mesmo sem barrar (achado investigando um bug real de duplicação de nó, 2026-07-22)."""
        self.client.force_login(self.admin)
        local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local", parent=self.regional
        )

        response = self.client.patch(
            reverse("hierarchy-node-detail", args=[local.id]), {"parent": local.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        local.refresh_from_db()
        self.assertEqual(local.parent_id, self.regional.id)

    def test_rejects_non_gerente_without_parent(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("hierarchy-node-list"),
            {"level": HierarchyNode.Level.LOCAL, "nome": "Local Órfão"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deactivating_node_with_legacy_invalid_parent_still_succeeds(self):
        """Um PATCH que só muda `ativo` não pode ser bloqueado por uma relação nível/pai
        inconsistente herdada de antes (ex.: sobra de um cargo removido) — a validação só deve
        reexaminar nível/pai quando um dos dois está de fato no payload."""
        self.client.force_login(self.admin)
        # Nível/pai inconsistente (VENDEDOR com pai LOCAL, deveria ser SUPERVISOR) — o model não
        # impede isso, só o serializer; simula um resto de dado já existente no banco.
        inconsistent = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Órfão Inconsistente", parent=self.regional
        )

        response = self.client.patch(
            reverse("hierarchy-node-detail", args=[inconsistent.id]), {"ativo": False}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        inconsistent.refresh_from_db()
        self.assertFalse(inconsistent.ativo)

    def test_deactivating_via_api_triggers_reassignment(self):
        group = ProductGroup.objects.create(nome="Embutidos")
        cycle = Cycle.objects.create(ano=2026, mes=7)
        local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local", parent=self.regional
        )
        gerente_user = User.objects.create_user(username="gerente", password="x", hierarchy_node=self.gerente)
        regional_user = User.objects.create_user(
            username="regional", password="x", hierarchy_node=self.regional
        )
        gerente_alloc = GoalAllocation.objects.create(
            cycle=cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=group,
            quantity_kg=100,
            criado_por=gerente_user,
        )
        (regional_alloc,) = DistributeGoalService.distribute(
            gerente_alloc,
            [
                ChildAllocationSpec(
                    owner_node_id=self.regional.id,
                    quantity_kg=100,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=group.id,
                )
            ],
            criado_por=gerente_user,
        )
        DistributeGoalService.distribute(
            regional_alloc,
            [
                ChildAllocationSpec(
                    owner_node_id=local.id,
                    quantity_kg=100,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=group.id,
                )
            ],
            criado_por=regional_user,
        )

        self.client.force_login(self.admin)
        response = self.client.patch(
            reverse("hierarchy-node-detail", args=[local.id]), {"ativo": False}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        regional_alloc.refresh_from_db()
        self.assertFalse(regional_alloc.distributed)


class FeristaCoverageApiTests(APITestCase):
    """Função do Administrador (Decisão 13): cadastrar quem cobriu quem, em qual mês."""

    def setUp(self):
        self.vendedor = HierarchyNode.objects.create(level=HierarchyNode.Level.VENDEDOR, nome="Titular")
        self.supervisor = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor"
        )
        self.admin = User.objects.create_user(username="admin", password="x", is_admin=True)
        self.plain_user = User.objects.create_user(
            username="user", password="x", hierarchy_node=self.vendedor
        )

    def test_non_admin_cannot_create_coverage(self):
        self.client.force_login(self.plain_user)

        response = self.client.post(
            reverse("ferista-coverage-list"),
            {"external_name": "FERISTA", "covered_node": self.vendedor.id, "ano": 2026, "mes": 3},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_any_authenticated_user_can_list(self):
        self.client.force_login(self.plain_user)

        response = self.client.get(reverse("ferista-coverage-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_create_coverage(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("ferista-coverage-list"),
            {"external_name": "FERISTA", "covered_node": self.vendedor.id, "ano": 2026, "mes": 3},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FeristaCoverage.objects.filter(external_name="FERISTA").exists())

    def test_rejects_covered_node_that_is_not_vendedor(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("ferista-coverage-list"),
            {"external_name": "FERISTA", "covered_node": self.supervisor.id, "ano": 2026, "mes": 3},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_duplicate_month_for_same_ferista(self):
        self.client.force_login(self.admin)
        FeristaCoverage.objects.create(external_name="FERISTA", covered_node=self.vendedor, ano=2026, mes=3)

        response = self.client.post(
            reverse("ferista-coverage-list"),
            {"external_name": "FERISTA", "covered_node": self.vendedor.id, "ano": 2026, "mes": 3},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_delete_coverage(self):
        self.client.force_login(self.admin)
        coverage = FeristaCoverage.objects.create(
            external_name="FERISTA", covered_node=self.vendedor, ano=2026, mes=3
        )

        response = self.client.delete(reverse("ferista-coverage-detail", args=[coverage.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FeristaCoverage.objects.filter(id=coverage.id).exists())
