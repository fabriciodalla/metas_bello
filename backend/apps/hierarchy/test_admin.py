from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.allocations.models import GoalAllocation
from apps.allocations.services import ChildAllocationSpec, DistributeGoalService
from apps.catalog.models import ProductGroup
from apps.cycles.models import Cycle

from .admin import HierarchyNodeAdmin
from .models import HierarchyNode

User = get_user_model()


class HierarchyNodeAdminSaveModelTests(TestCase):
    """Confirma que o Django Admin, via save_model, dispara O4 (HierarchyChangeReassignmentService)
    quando um nó é desativado ou reparentado — sem isso, a regra de negócio ficaria sem gatilho
    real no único lugar onde a hierarquia é editada (Decisão 4: CRUD só no Django Admin)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_user(
            username="admin", password="x", is_admin=True, is_staff=True
        )
        self.model_admin = HierarchyNodeAdmin(HierarchyNode, admin.site)

        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=7)
        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional", parent=self.gerente
        )
        self.local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local", parent=self.regional
        )

        gerente_user = User.objects.create_user(username="gerente", password="x", hierarchy_node=self.gerente)
        regional_user = User.objects.create_user(
            username="regional", password="x", hierarchy_node=self.regional
        )

        gerente_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=100,
            criado_por=gerente_user,
        )
        (self.regional_alloc,) = DistributeGoalService.distribute(
            gerente_allocation,
            [
                ChildAllocationSpec(
                    owner_node_id=self.regional.id,
                    quantity_kg=100,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                )
            ],
            criado_por=gerente_user,
        )
        DistributeGoalService.distribute(
            self.regional_alloc,
            [
                ChildAllocationSpec(
                    owner_node_id=self.local.id,
                    quantity_kg=100,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                )
            ],
            criado_por=regional_user,
        )

    def _request(self):
        request = self.factory.post("/admin/hierarchy/hierarchynode/")
        request.user = self.admin_user
        return request

    def test_deactivating_via_admin_triggers_reassignment(self):
        self.local.ativo = False

        self.model_admin.save_model(self._request(), self.local, form=None, change=True)

        self.regional_alloc.refresh_from_db()
        self.assertFalse(self.regional_alloc.distributed)

    def test_reparenting_via_admin_triggers_reassignment(self):
        outro_regional = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Outro Regional", parent=self.gerente
        )
        self.local.parent = outro_regional

        self.model_admin.save_model(self._request(), self.local, form=None, change=True)

        self.regional_alloc.refresh_from_db()
        self.assertFalse(self.regional_alloc.distributed)

    def test_unrelated_field_change_does_not_trigger_reassignment(self):
        self.local.nome = "Local Renomeado"

        self.model_admin.save_model(self._request(), self.local, form=None, change=True)

        self.regional_alloc.refresh_from_db()
        self.assertTrue(self.regional_alloc.distributed)

    def test_creating_a_new_node_does_not_trigger_reassignment(self):
        new_node = HierarchyNode(level=HierarchyNode.Level.LOCAL, nome="Novo Local", parent=self.regional)

        self.model_admin.save_model(self._request(), new_node, form=None, change=False)

        self.regional_alloc.refresh_from_db()
        self.assertTrue(self.regional_alloc.distributed)
