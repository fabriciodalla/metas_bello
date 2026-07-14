from django.conf import settings
from django.db import models


class GoalAllocationQuerySet(models.QuerySet):
    def visible_to(self, user):
        if user.is_admin:
            return self

        node_ids = list(user.hierarchy_nodes.values_list("id", flat=True))
        if not node_ids:
            return self.none()

        from apps.hierarchy.services import ScopeResolver

        return self.filter(owner_node_id__in=ScopeResolver.descendant_ids(node_ids))


class GoalAllocation(models.Model):
    class Granularity(models.TextChoices):
        GROUP = "GROUP", "Grupo"
        SUBGROUP = "SUBGROUP", "Subgrupo"
        PRODUCT = "PRODUCT", "Produto"

    objects = GoalAllocationQuerySet.as_manager()

    cycle = models.ForeignKey("cycles.Cycle", on_delete=models.PROTECT, related_name="allocations")
    owner_node = models.ForeignKey(
        "hierarchy.HierarchyNode", on_delete=models.PROTECT, related_name="allocations"
    )
    parent_allocation = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )

    granularity = models.CharField(max_length=10, choices=Granularity.choices)
    group = models.ForeignKey(
        "catalog.ProductGroup", null=True, blank=True, on_delete=models.PROTECT, related_name="allocations"
    )
    subgroup = models.ForeignKey(
        "catalog.ProductSubgroup", null=True, blank=True, on_delete=models.PROTECT, related_name="allocations"
    )
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, on_delete=models.PROTECT, related_name="allocations"
    )

    quantity_kg = models.PositiveIntegerField()
    distributed = models.BooleanField(default=False)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="allocations_criadas"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["cycle", "owner_node"]),
            models.Index(fields=["parent_allocation"]),
        ]
        constraints = [
            # Só o campo de produto compatível com a granularidade pode estar preenchido.
            models.CheckConstraint(
                condition=(
                    models.Q(
                        granularity="GROUP", group__isnull=False, subgroup__isnull=True, product__isnull=True
                    )
                    | models.Q(
                        granularity="SUBGROUP",
                        group__isnull=True,
                        subgroup__isnull=False,
                        product__isnull=True,
                    )
                    | models.Q(
                        granularity="PRODUCT",
                        group__isnull=True,
                        subgroup__isnull=True,
                        product__isnull=False,
                    )
                ),
                name="allocation_granularity_matches_target",
            ),
        ]

    def __str__(self):
        return f"{self.owner_node} — {self.quantity_kg}kg ({self.granularity})"
