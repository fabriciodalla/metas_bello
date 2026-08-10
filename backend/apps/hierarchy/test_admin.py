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
        self.local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local", parent=self.gerente
        )
        self.supervisor = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor", parent=self.local
        )

        gerente_user = User.objects.create_user(username="gerente", password="x", hierarchy_node=self.gerente)
        local_user = User.objects.create_user(username="local", password="x", hierarchy_node=self.local)

        gerente_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=100,
            criado_por=gerente_user,
        )
        (self.local_alloc,) = DistributeGoalService.distribute(
            gerente_allocation,
            [
                ChildAllocationSpec(
                    owner_node_id=self.local.id,
                    quantity_kg=100,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                )
            ],
            criado_por=gerente_user,
        )
        DistributeGoalService.distribute(
            self.local_alloc,
            [
                ChildAllocationSpec(
                    owner_node_id=self.supervisor.id,
                    quantity_kg=100,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                )
            ],
            criado_por=local_user,
        )

    def _request(self):
        request = self.factory.post("/admin/hierarchy/hierarchynode/")
        request.user = self.admin_user
        return request

    def test_deactivating_via_admin_triggers_reassignment(self):
        self.supervisor.ativo = False

        self.model_admin.save_model(self._request(), self.supervisor, form=None, change=True)

        self.local_alloc.refresh_from_db()
        self.assertFalse(self.local_alloc.distributed)

    def test_reparenting_via_admin_triggers_reassignment(self):
        outro_local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Outro Local", parent=self.gerente
        )
        self.supervisor.parent = outro_local

        self.model_admin.save_model(self._request(), self.supervisor, form=None, change=True)

        self.local_alloc.refresh_from_db()
        self.assertFalse(self.local_alloc.distributed)

    def test_unrelated_field_change_does_not_trigger_reassignment(self):
        self.supervisor.nome = "Supervisor Renomeado"

        self.model_admin.save_model(self._request(), self.supervisor, form=None, change=True)

        self.local_alloc.refresh_from_db()
        self.assertTrue(self.local_alloc.distributed)

    def test_creating_a_new_node_does_not_trigger_reassignment(self):
        new_node = HierarchyNode(
            level=HierarchyNode.Level.SUPERVISOR, nome="Novo Supervisor", parent=self.local
        )

        self.model_admin.save_model(self._request(), new_node, form=None, change=False)

        self.local_alloc.refresh_from_db()
        self.assertTrue(self.local_alloc.distributed)
