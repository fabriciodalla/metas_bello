from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.accounts import User
from api.models.calendar import Holiday, WorkingDaysConfig
from api.models.goals import GoalCycle
from api.routers.auth import get_current_user
from api.services.working_days import (
    _count_weekdays,
    calc_working_days,
    get_confirmed_working_days,
    previous_months,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])


# ── Schemas ────────────────────────────────────────────

class HolidayRead(BaseModel):
    id: int
    holiday_date: date
    year: int
    name: str
    model_config = {"from_attributes": True}


class HolidayCreate(BaseModel):
    holiday_date: date
    name: str


class HolidayBulkCreate(BaseModel):
    holidays: list[HolidayCreate]


class MonthWorkingDays(BaseModel):
    year: int
    month: int
    label: str
    weekdays: int
    holidays_count: int
    calculated_days: int
    confirmed_days: int | None
    effective_days: int
    is_target: bool


class WorkingDaysPreview(BaseModel):
    cycle_id: int
    target_month: int
    target_year: int
    months: list[MonthWorkingDays]


class MonthConfirm(BaseModel):
    year: int
    month: int
    confirmed_days: int

    @field_validator("confirmed_days")
    @classmethod
    def validate_days(cls, v: int) -> int:
        if v < 1 or v > 31:
            raise ValueError("Dias uteis deve estar entre 1 e 31")
        return v


class WorkingDaysUpdate(BaseModel):
    months: list[MonthConfirm]


# ── Holidays CRUD ──────────────────────────────────────

MONTH_NAMES = [
    "", "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


@router.get("/holidays", response_model=list[HolidayRead])
async def list_holidays(
    year: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Holiday).order_by(Holiday.holiday_date)
    if year is not None:
        query = query.where(Holiday.year == year)
    return (await db.execute(query)).scalars().all()


@router.post("/holidays", response_model=HolidayRead, status_code=201)
async def create_holiday(
    body: HolidayCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(Holiday).where(Holiday.holiday_date == body.holiday_date)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Feriado ja cadastrado nesta data")
    holiday = Holiday(
        holiday_date=body.holiday_date,
        year=body.holiday_date.year,
        name=body.name,
        created_by_id=current_user.id,
    )
    db.add(holiday)
    await db.commit()
    await db.refresh(holiday)
    return holiday


@router.post("/holidays/bulk", response_model=list[HolidayRead], status_code=201)
async def bulk_create_holidays(
    body: HolidayBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    created = []
    for item in body.holidays:
        existing = await db.execute(
            select(Holiday).where(Holiday.holiday_date == item.holiday_date)
        )
        if existing.scalar_one_or_none():
            continue
        holiday = Holiday(
            holiday_date=item.holiday_date,
            year=item.holiday_date.year,
            name=item.name,
            created_by_id=current_user.id,
        )
        db.add(holiday)
        created.append(holiday)
    await db.commit()
    for h in created:
        await db.refresh(h)
    return created


@router.delete("/holidays/{holiday_id}", status_code=204)
async def delete_holiday(
    holiday_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Holiday).where(Holiday.id == holiday_id))
    holiday = result.scalar_one_or_none()
    if not holiday:
        raise HTTPException(status_code=404, detail="Feriado nao encontrado")
    await db.delete(holiday)
    await db.commit()


# ── Working Days Preview & Update ──────────────────────

@router.get("/working-days/{cycle_id}", response_model=WorkingDaysPreview)
async def get_working_days_preview(
    cycle_id: int,
    db: AsyncSession = Depends(get_db),
):
    cycle = (await db.execute(
        select(GoalCycle).where(GoalCycle.id == cycle_id)
    )).scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")

    prev = previous_months(cycle.year, cycle.month, 3)
    all_months = list(reversed(prev)) + [(cycle.year, cycle.month)]

    months = []
    for y, m in all_months:
        calculated = await calc_working_days(db, y, m)
        confirmed = await get_confirmed_working_days(db, y, m)
        is_target = (y == cycle.year and m == cycle.month)

        if is_target and cycle.working_days:
            effective = cycle.working_days
            confirmed = cycle.working_days
        elif confirmed is not None:
            effective = confirmed
        else:
            effective = calculated

        holidays_result = await db.execute(
            select(Holiday).where(
                extract("year", Holiday.holiday_date) == y,
                extract("month", Holiday.holiday_date) == m,
            )
        )
        holidays_in_month = list(holidays_result.scalars().all())
        holidays_on_weekdays = sum(
            1 for h in holidays_in_month if h.holiday_date.weekday() < 5
        )

        weekdays = _count_weekdays(y, m)

        months.append(MonthWorkingDays(
            year=y,
            month=m,
            label=f"{MONTH_NAMES[m]}/{y}",
            weekdays=weekdays,
            holidays_count=holidays_on_weekdays,
            calculated_days=calculated,
            confirmed_days=confirmed,
            effective_days=effective,
            is_target=is_target,
        ))

    return WorkingDaysPreview(
        cycle_id=cycle_id,
        target_month=cycle.month,
        target_year=cycle.year,
        months=months,
    )


@router.put("/working-days/{cycle_id}", response_model=WorkingDaysPreview)
async def update_working_days(
    cycle_id: int,
    body: WorkingDaysUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle = (await db.execute(
        select(GoalCycle).where(GoalCycle.id == cycle_id)
    )).scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")

    for item in body.months:
        if item.year == cycle.year and item.month == cycle.month:
            cycle.working_days = item.confirmed_days

        existing = await db.execute(
            select(WorkingDaysConfig).where(
                WorkingDaysConfig.year == item.year,
                WorkingDaysConfig.month == item.month,
            )
        )
        config = existing.scalar_one_or_none()
        if config:
            config.confirmed_days = item.confirmed_days
            config.updated_by_id = current_user.id
        else:
            db.add(WorkingDaysConfig(
                year=item.year,
                month=item.month,
                confirmed_days=item.confirmed_days,
                updated_by_id=current_user.id,
            ))

    await db.commit()
    return await get_working_days_preview(cycle_id, db)
