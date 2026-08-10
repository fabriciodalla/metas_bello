from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.validators import RegexValidator
from django.db import models


class UserManager(DjangoUserManager):
    """Aceita `hierarchy_node=` como atalho de criação para o caso comum (um usuário, um nó) —
    o schema é M2M (O5, 1:N) desde a Decisão 10, mas a maioria dos usuários ainda ocupa só uma
    posição."""

    def create_user(self, username, email=None, password=None, hierarchy_node=None, **extra_fields):
        # E-mail é único e obrigatório (login passou a ser por e-mail); quem não passar um explícito
        # (testes, scripts internos) ganha um placeholder derivado do username em vez de colidir
        # com string vazia.
        user = super().create_user(
            username, email=email or f"{username}@levo.local", password=password, **extra_fields
        )
        if hierarchy_node is not None:
            user.hierarchy_nodes.add(hierarchy_node)
        return user

    def create_superuser(self, username, email=None, password=None, hierarchy_node=None, **extra_fields):
        user = super().create_superuser(
            username, email=email or f"{username}@levo.local", password=password, **extra_fields
        )
        if hierarchy_node is not None:
            user.hierarchy_nodes.add(hierarchy_node)
        return user


class User(AbstractUser):
    # Login é por e-mail, não por username — `username` aqui é o nome completo da pessoa (mesmo
    # texto do `HierarchyNode.nome`, mantidos em sincronia por `UserAccountSerializer`), não um
    # identificador técnico. Por isso troca o `UnicodeUsernameValidator` padrão (que rejeita
    # espaço) por um validador permissivo — só barra número, que não faz sentido num nome.
    username_validator = RegexValidator(
        regex=r"^[^\d]+$", message="Use o nome completo da pessoa, sem números."
    )
    username = models.CharField(
        "nome completo",
        max_length=150,
        unique=True,
        validators=[username_validator],
        error_messages={"unique": "Já existe um usuário com esse nome."},
    )
    is_admin = models.BooleanField(default=False)
    # Login é por e-mail (não por username) — precisa ser único. AbstractUser.email é blank e
    # sem unicidade por padrão, então sobrescrevemos aqui.
    email = models.EmailField(unique=True)
    # 1:N (O5, Decisão 10) — uma pessoa pode ocupar mais de uma posição/ramo ao mesmo tempo.
    hierarchy_nodes = models.ManyToManyField("hierarchy.HierarchyNode", blank=True, related_name="users")

    objects = UserManager()
