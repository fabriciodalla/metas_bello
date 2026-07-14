from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.models import ProductGroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import HierarchyNode

from .models import GoalAllocation
from .services import (
    AllocationClosureError,
    AllocationScopeError,
    ChildAllocationSpec,
    ClosureValidator,
    CycleCompletenessChecker,
    DistributeGoalService,
)

User = get_user_model()


class ClosureValidatorTests(TestCase):
    def test_accepts_when_sum_matches(self):
        ClosureValidator.validate(100, [60, 40])

    def test_rejects_when_sum_does_not_match(self):
        with self.assertRaises(AllocationClosureError):
            ClosureValidator.validate(100, [60, 30])

    def test_rejects_negative_quantity(self):
        with self.assertRaises(AllocationClosureError):
            ClosureValidator.validate(100, [110, -10])

    def test_rejects_non_integer_quantity(self):
        with self.assertRaises(AllocationClosureError):
            ClosureValidator.validate(100, [60.5, 39.5])


class DistributeGoalServiceTests(TestCase):
    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=7)
        self.gerente_node = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional A", parent=self.gerente_node
        )
        self.regional_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional B", parent=self.gerente_node
        )
        self.user = User.objects.create_user(
            username="gerente", password="x", hierarchy_node=self.gerente_node
        )
        self.parent_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente_node,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=100,
            criado_por=self.user,
        )

    def _children(self, qty_a, qty_b):
        return [
            ChildAllocationSpec(
                owner_node_id=self.regional_a.id,
                quantity_kg=qty_a,
                granularity=GoalAllocation.Granularity.GROUP,
                group_id=self.group.id,
            ),
            ChildAllocationSpec(
                owner_node_id=self.regional_b.id,
                quantity_kg=qty_b,
                granularity=GoalAllocation.Granularity.GROUP,
                group_id=self.group.id,
            ),
        ]

    def test_distribute_creates_children_and_marks_parent_distributed(self):
        created = DistributeGoalService.distribute(
            self.parent_allocation, self._children(60, 40), criado_por=self.user
        )

        self.assertEqual(len(created), 2)
        self.parent_allocation.refresh_from_db()
        self.assertTrue(self.parent_allocation.distributed)
        self.assertEqual(GoalAllocation.objects.filter(parent_allocation=self.parent_allocation).count(), 2)

    def test_distribute_rejects_mismatched_sum_and_rolls_back(self):
        with self.assertRaises(AllocationClosureError):
            DistributeGoalService.distribute(
                self.parent_allocation, self._children(60, 30), criado_por=self.user
            )

        self.parent_allocation.refresh_from_db()
        self.assertFalse(self.parent_allocation.distributed)
        self.assertEqual(GoalAllocation.objects.filter(parent_allocation=self.parent_allocation).count(), 0)

    def test_distribute_rejects_when_already_distributed(self):
        DistributeGoalService.distribute(self.parent_allocation, self._children(60, 40), criado_por=self.user)

        with self.assertRaises(AllocationClosureError):
            DistributeGoalService.distribute(
                self.parent_allocation, self._children(60, 40), criado_por=self.user
            )

    def test_distribute_rejects_when_user_does_not_own_parent(self):
        other_node = HierarchyNode.objects.create(level=HierarchyNode.Level.REGIONAL, nome="Outro Ramo")
        outsider = User.objects.create_user(username="outsider", password="x", hierarchy_node=other_node)

        with self.assertRaises(AllocationScopeError):
            DistributeGoalService.distribute(
                self.parent_allocation, self._children(60, 40), criado_por=outsider
            )

        self.parent_allocation.refresh_from_db()
        self.assertFalse(self.parent_allocation.distributed)

    def test_distribute_rejects_when_target_is_not_direct_child(self):
        grandchild = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Neto", parent=self.regional_a
        )
        children = [
            ChildAllocationSpec(
                owner_node_id=grandchild.id,
                quantity_kg=100,
                granularity=GoalAllocation.Granularity.GROUP,
                group_id=self.group.id,
            ),
        ]

        with self.assertRaises(AllocationScopeError):
            DistributeGoalService.distribute(self.parent_allocation, children, criado_por=self.user)


class CycleCompletenessCheckerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gerente", password="x")
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=7)
        self.gerente_node = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.regional = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional", parent=self.gerente_node
        )
        self.vendedor = HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor", parent=self.regional
        )
        self.gerente_allocation = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.gerente_node,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=100,
            criado_por=self.user,
        )

    def test_undistributed_intermediate_allocation_is_stuck(self):
        stuck = CycleCompletenessChecker.stuck_allocations(self.cycle)

        self.assertEqual(len(stuck), 1)
        self.assertEqual(stuck[0].allocation_id, self.gerente_allocation.id)
        self.assertFalse(CycleCompletenessChecker.is_complete(self.cycle))

    def test_undistributed_vendedor_allocation_is_not_stuck(self):
        GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.vendedor,
            parent_allocation=self.gerente_allocation,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=100,
            criado_por=self.user,
        )
        self.gerente_allocation.distributed = True
        self.gerente_allocation.save(update_fields=["distributed"])

        self.assertTrue(CycleCompletenessChecker.is_complete(self.cycle))
