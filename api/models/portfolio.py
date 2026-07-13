from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models import Base


class Client(Base):
    """Snapshot da carteira de clientes. Alimentada por query no ERP 1x por ciclo."""
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("cycle_id", "clifor", name="uq_client_cycle_clifor"),
        Index("ix_clients_cycle", "cycle_id"),
        Index("ix_clients_clifor", "clifor"),
        Index("ix_clients_seller_node", "seller_node_id"),
        Index("ix_clients_seller_name", "seller_name_normalized"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("goal_cycles.id"))
    clifor: Mapped[str] = mapped_column(String(40))
    cnpj: Mapped[str] = mapped_column(String(20), default="")
    client_name: Mapped[str] = mapped_column(String(200))
    seller_name_erp: Mapped[str] = mapped_column(String(200))
    seller_name_normalized: Mapped[str] = mapped_column(String(200))
    supervisor_code_erp: Mapped[str] = mapped_column(String(40), default="")
    municipality: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(50), default="")
    seller_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("hierarchy_nodes.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"Client(clifor={self.clifor!r}, seller={self.seller_name_normalized!r})"


class Accumulated(Base):
    """Historico de vendas do ERP. Alimentada por query 1x por ciclo."""
    __tablename__ = "accumulated"
    __table_args__ = (
        Index("ix_acc_cycle", "cycle_id"),
        Index("ix_acc_clifor", "clifor"),
        Index("ix_acc_seller", "seller_name_normalized"),
        Index("ix_acc_month", "month"),
        Index("ix_acc_product", "product_name_normalized"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("goal_cycles.id"))
    supervisor_code_erp: Mapped[str] = mapped_column(String(40), default="")
    seller_code_erp: Mapped[str] = mapped_column(String(40), default="")
    seller_name_erp: Mapped[str] = mapped_column(String(200))
    seller_name_normalized: Mapped[str] = mapped_column(String(200))
    clifor: Mapped[str] = mapped_column(String(40), default="")
    cnpj: Mapped[str] = mapped_column(String(20), default="")
    client_name: Mapped[str] = mapped_column(String(200), default="")
    month: Mapped[date] = mapped_column(Date)
    product_name_erp: Mapped[str] = mapped_column(String(200))
    product_name_normalized: Mapped[str] = mapped_column(String(200))
    total_kg: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    company_code_erp: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"Accumulated(clifor={self.clifor!r}, product={self.product_name_normalized!r}, {self.total_kg}kg)"


class BaseDistribution(Base):
    """Cruzamento clients x accumulated: vendedor da CARTEIRA + kg do ACUMULADO.
    Agrupado por vendedor / produto / mes."""
    __tablename__ = "base_distribution"
    __table_args__ = (
        Index("ix_base_cycle", "cycle_id"),
        Index("ix_base_seller_node", "seller_node_id"),
        Index("ix_base_month", "month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("goal_cycles.id"))
    seller_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("hierarchy_nodes.id"), nullable=True
    )
    seller_name: Mapped[str] = mapped_column(String(200))
    product_name: Mapped[str] = mapped_column(String(200))
    month: Mapped[date] = mapped_column(Date)
    total_kg: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"BaseDistribution(seller={self.seller_name!r}, product={self.product_name!r}, {self.total_kg}kg)"


# Alias para compatibilidade com portfolio_based engine
ClientPortfolio = Client
