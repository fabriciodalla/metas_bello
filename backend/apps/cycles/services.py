from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.allocations.services import CycleCompletenessChecker

from .models import Cycle


class CycleNotCompleteError(ValidationError):
    """Ciclo não pode fechar: há alocação intermediária ainda não distribuída."""


class CloseCycleService:
    """Gate de fechamento: só fecha o ciclo se 100% da meta chegou ao nível VENDEDOR."""

    @staticmethod
    @transaction.atomic
    def close(cycle: Cycle) -> Cycle:
        if cycle.status == Cycle.Status.FECHADO:
            raise CycleNotCompleteError("Ciclo já está fechado.")

        stuck = CycleCompletenessChecker.stuck_allocations(cycle)
        if stuck:
            total_stuck_kg = sum(item.quantity_kg for item in stuck)
            raise CycleNotCompleteError(
                f"Ciclo incompleto: {len(stuck)} alocação(ões) presa(s) totalizando {total_stuck_kg} kg."
            )

        cycle.status = Cycle.Status.FECHADO
        cycle.closed_at = timezone.now()
        cycle.save(update_fields=["status", "closed_at"])
        return cycle
