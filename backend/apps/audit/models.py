from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLogEntry(models.Model):
    """Histórico de mudanças em cadastros geridos pelo Administrador, e de reaberturas de meta.

    Cobre a hierarquia (HierarchyNode), o catálogo (ProductGroup/ProductSubgroup/Product) e
    GoalAllocation via GenericForeignKey — criação, inativação/reativação, mudança de vínculo
    (ex.: nó trocando de coordenação/supervisão) e reabertura de uma alocação já distribuída
    (H4, ver ReopenAllocationService em apps/allocations/services.py). Para hierarquia/catálogo,
    nada ainda popula esta tabela automaticamente; isso é trabalho de uma etapa futura (ver
    docs/roadmap.md). Para GoalAllocation, o próprio ReopenAllocationService já grava o evento.
    """

    class Action(models.TextChoices):
        CRIACAO = "CRIACAO", "Criação"
        ATUALIZACAO = "ATUALIZACAO", "Atualização"
        INATIVACAO = "INATIVACAO", "Inativação"
        REATIVACAO = "REATIVACAO", "Reativação"
        REABERTURA = "REABERTURA", "Reabertura"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    action = models.CharField(max_length=20, choices=Action.choices)
    changes = models.JSONField(default=dict, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="audit_entries"
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"])]
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.get_action_display()} — {self.content_type} #{self.object_id}"
