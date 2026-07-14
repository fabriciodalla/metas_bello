from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.hierarchy.models import HierarchyNode

User = get_user_model()


class AuthApiTests(APITestCase):
    def setUp(self):
        self.node = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")
        self.user = User.objects.create_user(
            username="gerente", password="senha-forte", hierarchy_node=self.node
        )

    def test_login_with_valid_credentials_returns_user_data(self):
        response = self.client.post(
            reverse("auth-login"), {"username": "gerente", "password": "senha-forte"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "gerente")
        self.assertEqual(response.data["hierarchy_nodes"][0]["id"], self.node.id)

    def test_login_with_invalid_credentials_is_rejected(self):
        response = self.client.post(
            reverse("auth-login"), {"username": "gerente", "password": "errada"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("auth-me"))

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_me_returns_current_user_when_authenticated(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "gerente")

    def test_logout_clears_session(self):
        self.client.force_login(self.user)
        self.client.post(reverse("auth-logout"))

        response = self.client.get(reverse("auth-me"))

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
