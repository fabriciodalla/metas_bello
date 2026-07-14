from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    """Aceita `hierarchy_node=` como atalho de criação para o caso comum (um usuário, um nó) —
    o schema é M2M (O5, 1:N) desde a Decisão 10, mas a maioria dos usuários ainda ocupa só uma
    posição."""

    def create_user(self, username, email=None, password=None, hierarchy_node=None, **extra_fields):
        user = super().create_user(username, email=email, password=password, **extra_fields)
        if hierarchy_node is not None:
            user.hierarchy_nodes.add(hierarchy_node)
        return user

    def create_superuser(self, username, email=None, password=None, hierarchy_node=None, **extra_fields):
        user = super().create_superuser(username, email=email, password=password, **extra_fields)
        if hierarchy_node is not None:
            user.hierarchy_nodes.add(hierarchy_node)
        return user


class User(AbstractUser):
    is_admin = models.BooleanField(default=False)
    # 1:N (O5, Decisão 10) — uma pessoa pode ocupar mais de uma posição/ramo ao mesmo tempo.
    hierarchy_nodes = models.ManyToManyField("hierarchy.HierarchyNode", blank=True, related_name="users")

    objects = UserManager()
