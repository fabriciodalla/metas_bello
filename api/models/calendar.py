from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from api.models import Base


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (
        UniqueConstraint("holiday_date", name="uq_holiday_date"),
        Index("ix_holidays_year", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holiday_date: Mapped[date] = mapped_column(Date)
    year: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(String(150))
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"Holiday({self.holiday_date}, {self.name!r})"


class WorkingDaysConfig(Base):
    __tablename__ = "working_days_config"
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_wd_year_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(SmallInteger)
    month: Mapped[int] = mapped_column(SmallInteger)
    confirmed_days: Mapped[int] = mapped_column(SmallInteger)
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"WorkingDaysConfig({self.month:02d}/{self.year}, {self.confirmed_days}d)"
