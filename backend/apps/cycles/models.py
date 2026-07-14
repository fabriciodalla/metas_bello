from django.db import models


class Cycle(models.Model):
    class Status(models.TextChoices):
        ABERTO = "ABERTO", "Aberto"
        FECHADO = "FECHADO", "Fechado"

    ano = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTO)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ano", "mes"], name="uniq_cycle_ano_mes"),
            models.CheckConstraint(condition=models.Q(mes__gte=1, mes__lte=12), name="cycle_mes_valido"),
        ]

    def __str__(self):
        return f"{self.mes:02d}/{self.ano} ({self.status})"
