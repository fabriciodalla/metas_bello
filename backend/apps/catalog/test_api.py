from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Product, ProductGroup, ProductSubgroup

User = get_user_model()


class CatalogApiTests(APITestCase):
    def setUp(self):
        self.embutidos = ProductGroup.objects.create(nome="Embutidos")
        self.frangos = ProductGroup.objects.create(nome="Frangos")
        self.linguica = ProductSubgroup.objects.create(nome="Linguiça", group=self.embutidos)
        self.salsicha = ProductSubgroup.objects.create(nome="Salsicha", group=self.embutidos)
        ProductSubgroup.objects.create(nome="Peito", group=self.frangos)
        self.product_a = Product.objects.create(nome="Linguiça Toscana", subgroup=self.linguica)
        self.product_b = Product.objects.create(nome="Salsicha Hot Dog", subgroup=self.salsicha)
        self.user = User.objects.create_user(username="user", password="x")
        self.client.force_login(self.user)

    def test_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("product-group-list"))

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_lists_groups(self):
        response = self.client.get(reverse("product-group-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_subgroups_filterable_by_group(self):
        response = self.client.get(reverse("product-subgroup-list"), {"group": self.embutidos.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {self.linguica.id, self.salsicha.id})

    def test_products_filterable_by_subgroup(self):
        response = self.client.get(reverse("product-list"), {"subgroup": self.linguica.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {self.product_a.id})
