from django.db import models


class HierarchyNodeQuerySet(models.QuerySet):
    def visible_to(self, user):
        if user.is_admin:
            return self

        node_ids = list(user.hierarchy_nodes.values_list("id", flat=True))
        if not node_ids:
            return self.none()

        from .services import ScopeResolver

        return self.filter(id__in=ScopeResolver.descendant_ids(node_ids))


class HierarchyNode(models.Model):
    class Level(models.TextChoices):
        GERENTE = "GERENTE", "Gerente"
        REGIONAL = "REGIONAL", "Coordenador Regional"
        LOCAL = "LOCAL", "Coordenador Local"
        SUPERVISOR = "SUPERVISOR", "Supervisor"
        VENDEDOR = "VENDEDOR", "Vendedor"

    objects = HierarchyNodeQuerySet.as_manager()

    level = models.CharField(max_length=20, choices=Level.choices)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    nome = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["level", "ativo"])]

    def __str__(self):
        return f"{self.get_level_display()}: {self.nome}"


class HierarchyClosure(models.Model):
    """Closure table: uma linha por par (ancestral, descendente), incluindo profundidade 0 (o próprio nó)."""

    ancestor = models.ForeignKey(HierarchyNode, on_delete=models.CASCADE, related_name="closure_descendants")
    descendant = models.ForeignKey(HierarchyNode, on_delete=models.CASCADE, related_name="closure_ancestors")
    depth = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ancestor", "descendant"], name="uniq_hierarchy_closure_pair"),
        ]
        indexes = [
            models.Index(fields=["ancestor"]),
            models.Index(fields=["descendant"]),
        ]


class ExternalSalespersonMapping(models.Model):
    """Mapeia o nome do vendedor exposto pela carteira do Postgres externo (`salesperson_name` em
    `DistributionBaseline`/`ClientPortfolioSnapshot` — texto livre, sem código estável) para o
    `HierarchyNode` interno correspondente. Parte de O3/O5 (ver docs/open-questions.md).

    Precisa ser populado manualmente (Django Admin) — não há casamento automático por nome: nome
    livre não é confiável o suficiente para atribuir histórico de vendas a um nó sem curadoria
    humana (nomes podem divergir em formatação, ter homônimos, ou mudar ao longo do tempo).
    """

    external_name = models.CharField(max_length=150, unique=True)
    hierarchy_node = models.ForeignKey(
        HierarchyNode, on_delete=models.PROTECT, related_name="external_salesperson_mappings"
    )

    def __str__(self):
        return f"{self.external_name} -> {self.hierarchy_node}"
