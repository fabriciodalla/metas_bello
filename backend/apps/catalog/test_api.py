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

    def test_non_admin_cannot_create_group(self):
        response = self.client.post(reverse("product-group-list"), {"nome": "Laticínios"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_does_not_see_inactive_groups(self):
        ProductGroup.objects.create(nome="Descontinuado", ativo=False)

        response = self.client.get(reverse("product-group-list"))

        self.assertEqual(len(response.data), 2)


class CatalogAdminApiTests(APITestCase):
    def setUp(self):
        self.embutidos = ProductGroup.objects.create(nome="Embutidos")
        self.inativo = ProductGroup.objects.create(nome="Descontinuado", ativo=False)
        self.admin = User.objects.create_user(username="admin", password="x", is_admin=True)
        self.client.force_login(self.admin)

    def test_admin_sees_inactive_groups(self):
        response = self.client.get(reverse("product-group-list"))

        ids = {item["id"] for item in response.data}
        self.assertIn(self.inativo.id, ids)

    def test_admin_can_create_group(self):
        # format="json" evita a semântica de "checkbox HTML" do DRF para multipart/form-data,
        # em que um BooleanField ausente vira False em vez de aplicar o default do model — não é
        # o formato que o frontend usa de verdade (sempre JSON via fetch).
        response = self.client.post(reverse("product-group-list"), {"nome": "Laticínios"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ProductGroup.objects.filter(nome="Laticínios", ativo=True).exists())

    def test_admin_can_inactivate_group(self):
        response = self.client.patch(
            reverse("product-group-detail", args=[self.embutidos.id]), {"ativo": False}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.embutidos.refresh_from_db()
        self.assertFalse(self.embutidos.ativo)

    def test_admin_can_create_and_inactivate_subgroup(self):
        create_response = self.client.post(
            reverse("product-subgroup-list"),
            {"nome": "Mussarela", "group": self.embutidos.id},
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(create_response.data["ativo"])
        subgroup_id = create_response.data["id"]

        patch_response = self.client.patch(
            reverse("product-subgroup-detail", args=[subgroup_id]), {"ativo": False}, format="json"
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertFalse(ProductSubgroup.objects.get(pk=subgroup_id).ativo)
