from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.models import ProductGroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import HierarchyNode

from .models import GoalAllocation
from .services import ChildAllocationSpec, DistributeGoalService

User = get_user_model()


class ScopeIsolationTests(TestCase):
    """Um usuário de um ramo nunca resolve nós/metas de outro ramo (critério de aceite do brief)."""

    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=7)

        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.local_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local A", parent=self.gerente
        )
        self.supervisor_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor A1", parent=self.local_a
        )
        self.local_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local B", parent=self.gerente
        )
        self.supervisor_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor B1", parent=self.local_b
        )

        self.user_a = User.objects.create_user(username="user_a", password="x", hierarchy_node=self.local_a)
        self.user_b = User.objects.create_user(username="user_b", password="x", hierarchy_node=self.local_b)
        self.admin_user = User.objects.create_user(username="admin", password="x", is_admin=True)
        self.no_node_user = User.objects.create_user(username="sem_no", password="x")

        self.allocation_a = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local_a,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=50,
            criado_por=self.user_a,
        )
        self.allocation_b = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local_b,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=50,
            criado_por=self.user_b,
        )

    def test_user_sees_only_own_branch_nodes(self):
        visible_ids = set(HierarchyNode.objects.visible_to(self.user_a).values_list("id", flat=True))

        self.assertEqual(visible_ids, {self.local_a.id, self.supervisor_a.id})
        self.assertNotIn(self.local_b.id, visible_ids)
        self.assertNotIn(self.supervisor_b.id, visible_ids)
        self.assertNotIn(self.gerente.id, visible_ids)

    def test_user_sees_only_own_branch_allocations(self):
        visible_ids = set(GoalAllocation.objects.visible_to(self.user_a).values_list("id", flat=True))

        self.assertEqual(visible_ids, {self.allocation_a.id})
        self.assertNotIn(self.allocation_b.id, visible_ids)

    def test_admin_sees_every_branch(self):
        node_ids = set(HierarchyNode.objects.visible_to(self.admin_user).values_list("id", flat=True))
        allocation_ids = set(GoalAllocation.objects.visible_to(self.admin_user).values_list("id", flat=True))

        self.assertEqual(
            node_ids,
            {self.gerente.id, self.local_a.id, self.supervisor_a.id, self.local_b.id, self.supervisor_b.id},
        )
        self.assertEqual(allocation_ids, {self.allocation_a.id, self.allocation_b.id})

    def test_user_without_node_sees_nothing(self):
        self.assertEqual(HierarchyNode.objects.visible_to(self.no_node_user).count(), 0)
        self.assertEqual(GoalAllocation.objects.visible_to(self.no_node_user).count(), 0)


class MultiNodeUserScopeTests(TestCase):
    """O5 (1:N, Decisão 10): uma pessoa pode ocupar mais de uma posição/ramo ao mesmo tempo —
    o escopo visível e as checagens de posse precisam unir todos os nós do usuário, não só um."""

    def setUp(self):
        self.group = ProductGroup.objects.create(nome="Embutidos")
        self.cycle = Cycle.objects.create(ano=2026, mes=7)

        self.gerente = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.local_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local A", parent=self.gerente
        )
        self.supervisor_a = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor A1", parent=self.local_a
        )
        self.local_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local B", parent=self.gerente
        )
        self.supervisor_b = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor B1", parent=self.local_b
        )

        # Uma pessoa só, ocupando Local A e Local B ao mesmo tempo.
        self.multi_user = User.objects.create_user(username="multi", password="x")
        self.multi_user.hierarchy_nodes.add(self.local_a, self.local_b)

        self.allocation_a = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local_a,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=50,
            criado_por=self.multi_user,
        )
        self.allocation_b = GoalAllocation.objects.create(
            cycle=self.cycle,
            owner_node=self.local_b,
            granularity=GoalAllocation.Granularity.GROUP,
            group=self.group,
            quantity_kg=30,
            criado_por=self.multi_user,
        )

    def test_multi_node_user_sees_the_union_of_both_branches(self):
        node_ids = set(HierarchyNode.objects.visible_to(self.multi_user).values_list("id", flat=True))

        self.assertEqual(
            node_ids, {self.local_a.id, self.supervisor_a.id, self.local_b.id, self.supervisor_b.id}
        )
        self.assertNotIn(self.gerente.id, node_ids)

    def test_multi_node_user_sees_allocations_from_both_branches(self):
        allocation_ids = set(GoalAllocation.objects.visible_to(self.multi_user).values_list("id", flat=True))

        self.assertEqual(allocation_ids, {self.allocation_a.id, self.allocation_b.id})

    def test_multi_node_user_can_distribute_allocations_owned_by_either_node(self):
        result_a = DistributeGoalService.distribute(
            self.allocation_a,
            [
                ChildAllocationSpec(
                    owner_node_id=self.supervisor_a.id,
                    quantity_kg=50,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                )
            ],
            criado_por=self.multi_user,
        )
        result_b = DistributeGoalService.distribute(
            self.allocation_b,
            [
                ChildAllocationSpec(
                    owner_node_id=self.supervisor_b.id,
                    quantity_kg=30,
                    granularity=GoalAllocation.Granularity.GROUP,
                    group_id=self.group.id,
                )
            ],
            criado_por=self.multi_user,
        )

        self.assertEqual(len(result_a), 1)
        self.assertEqual(len(result_b), 1)
