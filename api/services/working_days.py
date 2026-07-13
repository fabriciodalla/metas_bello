"""Calculo de dias uteis considerando feriados e overrides do admin."""
from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.calendar import Holiday, WorkingDaysConfig


def _count_weekdays(year: int, month: int) -> int:
    total = 0
    num_days = calendar.monthrange(year, month)[1]
    for day in range(1, num_days + 1):
        if date(year, month, day).weekday() < 5:
            total += 1
    return total


async def count_holidays_in_month(db: AsyncSession, year: int, month: int) -> int:
    result = await db.execute(
        select(Holiday).where(
            extract("year", Holiday.holiday_date) == year,
            extract("month", Holiday.holiday_date) == month,
        )
    )
    holidays = list(result.scalars().all())
    return sum(1 for h in holidays if h.holiday_date.weekday() < 5)


async def calc_working_days(db: AsyncSession, year: int, month: int) -> int:
    weekdays = _count_weekdays(year, month)
    holidays_on_weekdays = await count_holidays_in_month(db, year, month)
    return weekdays - holidays_on_weekdays


async def get_confirmed_working_days(
    db: AsyncSession, year: int, month: int
) -> int | None:
    result = await db.execute(
        select(WorkingDaysConfig.confirmed_days).where(
            WorkingDaysConfig.year == year,
            WorkingDaysConfig.month == month,
        )
    )
    return result.scalar_one_or_none()


async def get_effective_working_days(
    db: AsyncSession, year: int, month: int
) -> int:
    confirmed = await get_confirmed_working_days(db, year, month)
    if confirmed is not None:
        return confirmed
    return await calc_working_days(db, year, month)


def previous_months(year: int, month: int, count: int = 3, skip: int = 1) -> list[tuple[int, int]]:
    """Retorna os `count` meses anteriores, pulando `skip` meses.

    Regra de negócio: o ciclo é sempre para o mês seguinte ao atual.
    Os 3 meses de histórico são os 3 meses FECHADOS antes do mês atual.
    skip=1 (padrão) pula o mês imediatamente anterior ao ciclo (mês atual,
    que ainda não fechou).

    Exemplo: ciclo=07/2026, skip=1 → pula junho, retorna maio, abril, março.
    """
    result = []
    y, m = year, month
    for _ in range(skip + count):
        m -= 1
        if m < 1:
            m = 12
            y -= 1
        if _ >= skip:
            result.append((y, m))
    return result
