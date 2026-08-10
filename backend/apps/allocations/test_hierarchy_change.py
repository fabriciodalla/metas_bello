from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.audit.models import AuditLogEntry
from apps.catalog.models import ProductGroup, ProductSubgroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import HierarchyNode

from .models import GoalAllocation
from .services import ChildAllocationSpec, DistributeGoalService, HierarchyChangeReassignmentService

User = get_user_model()


class HierarchyChangeReassignmentServiceTests(TestCase):
    """O4: quando a hierarquia muda (nó desativado ou reparentado) com meta em ciclo aberto, a
    meta volta pro nó pai (alocação-pai é reaberta), que precisa redistribuir."""

    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.subgroup = ProductSubgroup.objects.create(nome="Linguiça", group=self.group)
        self.cycle = Cycle.objects.create(ano=2026, mes=7)

        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.local_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local A", parent=self.gerente
        )
        self.local_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local B", parent=self.gerente
        )
        self.supervisor_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor A", parent=self.local_a
        )
        self.vendedor_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor A", parent=self.supervisor_a
        )

        self.gerente_user = User.objects.create_user(
            username="gerente", password="x", hierarchy_node=self.gerente
        )
        self.local_a_user = User.objects.create_user(
            username="local_a", password="x", hierarchy_node=self.local_a
        )
        self.supervisor_a_user = User.objects.create_user(
            username="supervisor_a", password="x", hierarchy_node=self.supervisor_a
        )
        self.admin_user = User.objects.create_user(username="admin", password="x", is_admin=True)

        self.gerente_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=1000,
            criado_por=self.gerente_user,
        )

    def _distribute_full_chain(self):
        self.local_a_alloc, self.local_b_alloc = DistributeGoalService.distribute(
            self.gerente_allocation,
            [
                ChildAllocationSpec(
                    owner_node_id=self.local_a.id,
                    quantity_kg=600,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                ),
                ChildAllocationSpec(
                    owner_node_id=self.local_b.id,
                    quantity_kg=400,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                ),
            ],
            criado_por=self.gerente_user,
        )
        (self.supervisor_a_alloc,) = DistributeGoalService.distribute(
            self.local_a_alloc,
            [
                ChildAllocationSpec(
                    owner_node_id=self.supervisor_a.id,
                    quantity_kg=600,
                    granularity=GoalAllocation.Granularity.SUBGROUP,
                    subgroup_id=self.subgroup.id,
                )
            ],
            criado_por=self.local_a_user,
        )
        DistributeGoalService.distribute(
            self.supervisor_a_alloc,
            [
                ChildAllocationSpec(
                    owner_node_id=self.vendedor_a.id,
                    quantity_kg=600,
                    granularity=GoalAllocation.Granularity.SUBGROUP,
                    subgroup_id=self.subgroup.id,
                )
            ],
            criado_por=self.supervisor_a_user,
        )

    def test_deactivating_a_node_reopens_the_parent_allocation(self):
        self._distribute_full_chain()

        self.local_a.ativo = False
        self.local_a.save()

        HierarchyChangeReassignmentService.reassign_open_cycle_allocations(
            self.local_a, changed_by=self.admin_user
        )

        self.gerente_allocation.refresh_from_db()
        self.assertFalse(self.gerente_allocation.distributed)
        # Toda a sub-árvore do Gerente (Local A E Local B) foi invalidada — não dá pra "devolver"
        # só a fatia de Local A sem redistribuir o total do Gerente de novo.
        self.assertFalse(GoalAllocation.objects.filter(id=self.local_a_alloc.id).exists())
        self.assertFalse(GoalAllocation.objects.filter(id=self.local_b_alloc.id).exists())
        self.assertFalse(GoalAllocation.objects.filter(id=self.supervisor_a_alloc.id).exists())

    def test_reparenting_a_node_reopens_the_parent_allocation(self):
        self._distribute_full_chain()
        outro_local = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Outro Local", parent=self.gerente
        )

        self.supervisor_a.parent = outro_local
        self.supervisor_a.save()

        HierarchyChangeReassignmentService.reassign_open_cycle_allocations(
            self.supervisor_a, changed_by=self.admin_user
        )

        self.local_a_alloc.refresh_from_db()
        self.assertFalse(self.local_a_alloc.distributed)

    def test_records_audit_log_entry_with_hierarchy_change_reason(self):
        self._distribute_full_chain()
        self.local_a.ativo = False
        self.local_a.save()

        HierarchyChangeReassignmentService.reassign_open_cycle_allocations(
            self.local_a, changed_by=self.admin_user
        )

        entry = AuditLogEntry.objects.get(
            content_type__model="goalallocation", object_id=self.gerente_allocation.id
        )
        self.assertEqual(entry.action, AuditLogEntry.Action.REABERTURA)
        self.assertEqual(entry.changed_by, self.admin_user)
        self.assertEqual(entry.changes["motivo"], "mudanca_hierarquia")
        self.assertEqual(entry.changes["no_afetado_id"], self.local_a.id)

    def test_no_effect_when_node_has_no_open_cycle_allocation(self):
        no_op_node = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Sem Meta", parent=self.gerente
        )

        result = HierarchyChangeReassignmentService.reassign_open_cycle_allocations(
            no_op_node, changed_by=self.admin_user
        )

        self.assertEqual(result, [])

    def test_calling_again_after_already_reopened_is_a_safe_no_op(self):
        self._distribute_full_chain()
        self.local_a.ativo = False
        self.local_a.save()
        HierarchyChangeReassignmentService.reassign_open_cycle_allocations(
            self.local_a, changed_by=self.admin_user
        )

        # A alocação de Local A já foi apagada na cascata acima; chamar de novo não deve estourar
        # erro (não há mais nada com esse owner_node pra reabrir).
        result = HierarchyChangeReassignmentService.reassign_open_cycle_allocations(
            self.local_a, changed_by=self.admin_user
        )

        self.assertEqual(result, [])

    def test_reopens_the_shared_parent_only_once_when_node_has_two_groups(self):
        other_group = ProductGroup.objects.create(nome="Frangos")
        other_gerente_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=other_group,
            quantity_kg=200,
            criado_por=self.gerente_user,
        )
        self._distribute_full_chain()
        DistributeGoalService.distribute(
            other_gerente_allocation,
            [
                ChildAllocationSpec(
                    owner_node_id=self.local_a.id,
                    quantity_kg=200,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=other_group.id,
                )
            ],
            criado_por=self.gerente_user,
        )
        # Local A agora tem duas alocações próprias (Embutidos e Frangos), com pais diferentes.

        result = HierarchyChangeReassignmentService.reassign_open_cycle_allocations(
            self.local_a, changed_by=self.admin_user
        )

        reopened_ids = {allocation.id for allocation in result}
        self.assertEqual(reopened_ids, {self.gerente_allocation.id, other_gerente_allocation.id})
