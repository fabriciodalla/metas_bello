from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.allocations.models import GoalAllocation
from apps.catalog.models import ProductGroup, ProductSubgroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import HierarchyNode

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Semeia um cenário mínimo de demonstração (hierarquia de 5 níveis, catálogo, ciclo aberto, "
        "usuários e uma alocação raiz pendente). Só para ambiente de desenvolvimento."
    )

    def handle(self, *args, **options):
        if HierarchyNode.objects.exists():
            self.stdout.write(
                self.style.WARNING("Já existem dados — rode 'manage.py flush' antes, se quiser recriar.")
            )
            return

        group = ProductGroup.objects.create(nome="Embutidos")
        ProductSubgroup.objects.create(nome="Linguica", group=group)
        ProductSubgroup.objects.create(nome="Salsicha", group=group)

        cycle = Cycle.objects.create(ano=2026, mes=7)

        gerente_node = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente Bello")
        regional_node = HierarchyNode.objects.create(
            level=HierarchyNode.Level.REGIONAL, nome="Regional Sul", parent=gerente_node
        )
        local_node = HierarchyNode.objects.create(
            level=HierarchyNode.Level.LOCAL, nome="Local Curitiba", parent=regional_node
        )
        supervisor_node = HierarchyNode.objects.create(
            level=HierarchyNode.Level.SUPERVISOR, nome="Supervisor A", parent=local_node
        )
        HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor 1", parent=supervisor_node
        )
        HierarchyNode.objects.create(
            level=HierarchyNode.Level.VENDEDOR, nome="Vendedor 2", parent=supervisor_node
        )

        # Administrador (H3/Decisão 4): CRUD via Django Admin, sem posição na cascata de metas —
        # papel separado do Gerente, mesmo que a mesma pessoa possa ocupar os dois na vida real.
        admin_user = User.objects.create_superuser(
            username="admin", password="admin12345", email="admin@bello.local"
        )
        admin_user.is_admin = True
        admin_user.save()

        gerente_user = User.objects.create_user(
            username="gerente",
            password="senha12345",
            email="gerente@bello.local",
            hierarchy_node=gerente_node,
        )
        User.objects.create_user(
            username="regional",
            password="senha12345",
            email="regional@bello.local",
            hierarchy_node=regional_node,
        )
        User.objects.create_user(
            username="local", password="senha12345", email="local@bello.local", hierarchy_node=local_node
        )
        User.objects.create_user(
            username="supervisor",
            password="senha12345",
            email="supervisor@bello.local",
            hierarchy_node=supervisor_node,
        )

        GoalAllocation.objects.create(
            cycle=cycle,
            owner_node=gerente_node,
            granularity=GoalAllocation.Granularity.GROUP,
            group=group,
            quantity_kg=1000,
            criado_por=gerente_user,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seed criado. Login por e-mail: admin@bello.local / admin12345 (Administrador, sem "
                "posição na hierarquia); gerente@bello.local / senha12345 (demais usuários seguem o "
                "mesmo padrão {username}@bello.local, senha senha12345)."
            )
        )
