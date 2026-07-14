from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.hierarchy.models import HierarchyNode

User = get_user_model()


class UserManagerHierarchyNodeConvenienceTests(TestCase):
    """`create_user(hierarchy_node=...)` é um atalho de conveniência sobre o M2M `hierarchy_nodes`
    (O5, Decisão 10) — não é o modelo de dados real, só facilita o caso comum (1 nó)."""

    def test_create_user_with_hierarchy_node_attaches_exactly_one_node(self):
        node = HierarchyNode.objects.create(level=HierarchyNode.Level.VENDEDOR, nome="Vendedor")

        user = User.objects.create_user(username="fulano", password="x", hierarchy_node=node)

        self.assertEqual(list(user.hierarchy_nodes.all()), [node])

    def test_create_user_without_hierarchy_node_attaches_nothing(self):
        user = User.objects.create_user(username="sem_no", password="x")

        self.assertEqual(user.hierarchy_nodes.count(), 0)

    def test_a_user_can_be_attached_to_more_than_one_node(self):
        node_a = HierarchyNode.objects.create(level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor A")
        node_b = HierarchyNode.objects.create(level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor B")
        user = User.objects.create_user(username="multi", password="x")

        user.hierarchy_nodes.add(node_a, node_b)

        self.assertEqual(set(user.hierarchy_nodes.values_list("id", flat=True)), {node_a.id, node_b.id})
