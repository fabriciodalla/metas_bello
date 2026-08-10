from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.audit.models import AuditLogEntry
from apps.catalog.models import ProductGroup, ProductSubgroup
from apps.cycles.models import Cycle
from apps.cycles.services import CloseCycleService
from apps.hierarchy.models import HierarchyNode

from .models import GoalAllocation
from .services import (
    AllocationReopenError,
    AllocationScopeError,
    ChildAllocationSpec,
    CycleCompletenessChecker,
    DistributeGoalService,
    ReopenAllocationService,
)

User = get_user_model()


class ReopenAllocationServiceTests(TestCase):
    """H4: uma alocação já distribuída pode ser reaberta pelo nível que a distribuiu, enquanto
    o ciclo está aberto, invalidando em cascata a sub-árvore de filhas."""

    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.subgroup = ProductSubgroup.objects.create(nome="Linguiça", group=self.group)
        self.cycle = Cycle.objects.create(ano=2026, mes=7)

        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")

        self.regional_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional A", parent=self.gerente
        )
        self.local_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local A", parent=self.regional_a
        )
        self.supervisor_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor A", parent=self.local_a
        )
        self.vendedor_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor A", parent=self.supervisor_a
        )

        self.regional_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional B", parent=self.gerente
        )
        self.local_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local B", parent=self.regional_b
        )
        self.supervisor_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor B", parent=self.local_b
        )
        self.vendedor_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor B", parent=self.supervisor_b
        )

        self.gerente_user = User.objects.create_user(
            username="gerente", password="x", hierarchy_node=self.gerente
        )
        self.regional_a_user = User.objects.create_user(
            username="regional_a", password="x", hierarchy_node=self.regional_a
        )
        self.local_a_user = User.objects.create_user(
            username="local_a", password="x", hierarchy_node=self.local_a
        )
        self.supervisor_a_user = User.objects.create_user(
            username="supervisor_a", password="x", hierarchy_node=self.supervisor_a
        )
        self.regional_b_user = User.objects.create_user(
            username="regional_b", password="x", hierarchy_node=self.regional_b
        )
        self.local_b_user = User.objects.create_user(
            username="local_b", password="x", hierarchy_node=self.local_b
        )
        self.supervisor_b_user = User.objects.create_user(
            username="supervisor_b", password="x", hierarchy_node=self.supervisor_b
        )

        self.gerente_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=1000,
            criado_por=self.gerente_user,
        )

    def _distribute_gerente_to_both_regionais(self):
        return DistributeGoalService.distribute(
            self.gerente_allocation,
            [
                ChildAllocationSpec(
                    owner_node_id=self.regional_a.id,
                    quantity_kg=600,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                ),
                ChildAllocationSpec(
                    owner_node_id=self.regional_b.id,
                    quantity_kg=400,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                ),
            ],
            criado_por=self.gerente_user,
        )

    def _distribute_branch_down(self, regional_alloc, local, supervisor, vendedor, users, qty):
        (local_alloc,) = DistributeGoalService.distribute(
            regional_alloc,
            [
                ChildAllocationSpec(
                    owner_node_id=local.id,
                    quantity_kg=qty,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                )
            ],
            criado_por=users[0],
        )
        (supervisor_alloc,) = DistributeGoalService.distribute(
            local_alloc,
            [
                ChildAllocationSpec(
                    owner_node_id=supervisor.id,
                    quantity_kg=qty,
                    granularity=GoalAllocation.Granularity.SUBGROUP,
                    subgroup_id=self.subgroup.id,
                )
            ],
            criado_por=users[1],
        )
        (vendedor_alloc,) = DistributeGoalService.distribute(
            supervisor_alloc,
            [
                ChildAllocationSpec(
                    owner_node_id=vendedor.id,
                    quantity_kg=qty,
                    granularity=GoalAllocation.Granularity.SUBGROUP,
                    subgroup_id=self.subgroup.id,
                )
            ],
            criado_por=users[2],
        )
        return local_alloc, supervisor_alloc, vendedor_alloc

    def test_reopen_cascades_delete_and_resets_distributed_flag(self):
        regional_alloc_a, _regional_alloc_b = self._distribute_gerente_to_both_regionais()
        local_alloc, supervisor_alloc, vendedor_alloc = self._distribute_branch_down(
            regional_alloc_a,
            self.local_a,
            self.supervisor_a,
            self.vendedor_a,
            [self.regional_a_user, self.local_a_user, self.supervisor_a_user],
            qty=600,
        )

        ReopenAllocationService.reopen(regional_alloc_a, criado_por=self.regional_a_user)

        regional_alloc_a.refresh_from_db()
        self.assertFalse(regional_alloc_a.distributed)
        self.assertFalse(GoalAllocation.objects.filter(id=local_alloc.id).exists())
        self.assertFalse(GoalAllocation.objects.filter(id=supervisor_alloc.id).exists())
        self.assertFalse(GoalAllocation.objects.filter(id=vendedor_alloc.id).exists())

    def test_reopen_creates_audit_log_entry(self):
        regional_alloc_a, _regional_alloc_b = self._distribute_gerente_to_both_regionais()
        local_alloc, supervisor_alloc, vendedor_alloc = self._distribute_branch_down(
            regional_alloc_a,
            self.local_a,
            self.supervisor_a,
            self.vendedor_a,
            [self.regional_a_user, self.local_a_user, self.supervisor_a_user],
            qty=600,
        )

        ReopenAllocationService.reopen(regional_alloc_a, criado_por=self.regional_a_user)

        entry = AuditLogEntry.objects.get(content_type__model="goalallocation", object_id=regional_alloc_a.id)
        self.assertEqual(entry.action, AuditLogEntry.Action.REABERTURA)
        self.assertEqual(entry.changed_by, self.regional_a_user)
        invalidated_ids = {item["id"] for item in entry.changes["filhas_invalidadas"]}
        self.assertEqual(invalidated_ids, {local_alloc.id, supervisor_alloc.id, vendedor_alloc.id})

    def test_reopen_is_scoped_to_the_branch_only(self):
        regional_alloc_a, regional_alloc_b = self._distribute_gerente_to_both_regionais()
        self._distribute_branch_down(
            regional_alloc_a,
            self.local_a,
            self.supervisor_a,
            self.vendedor_a,
            [self.regional_a_user, self.local_a_user, self.supervisor_a_user],
            qty=600,
        )
        local_alloc_b, supervisor_alloc_b, vendedor_alloc_b = self._distribute_branch_down(
            regional_alloc_b,
            self.local_b,
            self.supervisor_b,
            self.vendedor_b,
            [self.regional_b_user, self.local_b_user, self.supervisor_b_user],
            qty=400,
        )

        ReopenAllocationService.reopen(regional_alloc_a, criado_por=self.regional_a_user)

        # O ramo B, irmão não tocado, permanece intacto.
        self.assertTrue(GoalAllocation.objects.filter(id=local_alloc_b.id, distributed=True).exists())
        self.assertTrue(GoalAllocation.objects.filter(id=supervisor_alloc_b.id).exists())
        self.assertTrue(GoalAllocation.objects.filter(id=vendedor_alloc_b.id).exists())
        regional_alloc_b.refresh_from_db()
        self.assertTrue(regional_alloc_b.distributed)

    def test_reopen_rejects_when_caller_does_not_own_allocation(self):
        regional_alloc_a, _regional_alloc_b = self._distribute_gerente_to_both_regionais()
        self._distribute_branch_down(
            regional_alloc_a,
            self.local_a,
            self.supervisor_a,
            self.vendedor_a,
            [self.regional_a_user, self.local_a_user, self.supervisor_a_user],
            qty=600,
        )

        with self.assertRaises(AllocationScopeError):
            ReopenAllocationService.reopen(regional_alloc_a, criado_por=self.regional_b_user)

        regional_alloc_a.refresh_from_db()
        self.assertTrue(regional_alloc_a.distributed)

    def test_reopen_rejects_when_not_yet_distributed(self):
        with self.assertRaises(AllocationReopenError):
            ReopenAllocationService.reopen(self.gerente_allocation, criado_por=self.gerente_user)

    def test_reopen_rejects_when_cycle_is_closed(self):
        regional_alloc_a, regional_alloc_b = self._distribute_gerente_to_both_regionais()
        self._distribute_branch_down(
            regional_alloc_a,
            self.local_a,
            self.supervisor_a,
            self.vendedor_a,
            [self.regional_a_user, self.local_a_user, self.supervisor_a_user],
            qty=600,
        )
        self._distribute_branch_down(
            regional_alloc_b,
            self.local_b,
            self.supervisor_b,
            self.vendedor_b,
            [self.regional_b_user, self.local_b_user, self.supervisor_b_user],
            qty=400,
        )
        CloseCycleService.close(self.cycle)

        with self.assertRaises(AllocationReopenError):
            ReopenAllocationService.reopen(regional_alloc_b, criado_por=self.regional_b_user)

    def test_reopen_makes_cycle_incomplete_again_and_redistribute_closes_it_back(self):
        regional_alloc_a, regional_alloc_b = self._distribute_gerente_to_both_regionais()
        self._distribute_branch_down(
            regional_alloc_a,
            self.local_a,
            self.supervisor_a,
            self.vendedor_a,
            [self.regional_a_user, self.local_a_user, self.supervisor_a_user],
            qty=600,
        )
        self._distribute_branch_down(
            regional_alloc_b,
            self.local_b,
            self.supervisor_b,
            self.vendedor_b,
            [self.regional_b_user, self.local_b_user, self.supervisor_b_user],
            qty=400,
        )
        self.assertTrue(CycleCompletenessChecker.is_complete(self.cycle))

        ReopenAllocationService.reopen(regional_alloc_a, criado_por=self.regional_a_user)
        self.assertFalse(CycleCompletenessChecker.is_complete(self.cycle))

        # A mesma DistributeGoalService, sem nenhuma mudança, refaz o repasse normalmente.
        self._distribute_branch_down(
            regional_alloc_a,
            self.local_a,
            self.supervisor_a,
            self.vendedor_a,
            [self.regional_a_user, self.local_a_user, self.supervisor_a_user],
            qty=600,
        )

        self.assertTrue(CycleCompletenessChecker.is_complete(self.cycle))
        CloseCycleService.close(self.cycle)
        self.cycle.refresh_from_db()
        self.assertEqual(self.cycle.status, Cycle.Status.FECHADO)
