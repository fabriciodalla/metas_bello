from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import HierarchyNode

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
