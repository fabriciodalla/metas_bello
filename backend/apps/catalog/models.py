from django.db import models


class ProductGroup(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class ProductSubgroup(models.Model):
    nome = models.CharField(max_length=100)
    group = models.ForeignKey(ProductGroup, on_delete=models.PROTECT, related_name="subgroups")
    ativo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["group", "nome"], name="uniq_subgroup_nome_por_group"),
        ]

    def __str__(self):
        return f"{self.group.nome} / {self.nome}"


class Product(models.Model):
    """Só necessário se a granularidade do Vendedor for produto (ver open-questions.md O1)."""

    nome = models.CharField(max_length=255)
    subgroup = models.ForeignKey(ProductSubgroup, on_delete=models.PROTECT, related_name="products")
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class ExternalProductMapping(models.Model):
    """Mapeia identificadores do Postgres externo (histórico de vendas) para o catálogo interno (ver O3)."""

    external_code = models.CharField(max_length=100, unique=True)
    group = models.ForeignKey(
        ProductGroup, null=True, blank=True, on_delete=models.CASCADE, related_name="external_mappings"
    )
    subgroup = models.ForeignKey(
        ProductSubgroup, null=True, blank=True, on_delete=models.CASCADE, related_name="external_mappings"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(group__isnull=False, subgroup__isnull=True)
                    | models.Q(group__isnull=True, subgroup__isnull=False)
                ),
                name="external_mapping_targets_exactly_one",
            ),
        ]
