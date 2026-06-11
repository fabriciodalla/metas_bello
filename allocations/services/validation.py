from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class DistributionClosureResult:
    can_send: bool
    difference_kg: Decimal


def _as_decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def evaluate_distribution_closure(
    received_kg: Decimal | int | str,
    allocated_kg_values: Iterable[Decimal | int | str],
) -> DistributionClosureResult:
    received = _as_decimal(received_kg)
    allocated_total = sum((_as_decimal(value) for value in allocated_kg_values), Decimal("0"))
    difference = received - allocated_total

    return DistributionClosureResult(
        can_send=difference == Decimal("0"),
        difference_kg=difference,
    )
