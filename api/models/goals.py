from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models import Base

CYCLE_STATUSES = ("RASCUNHO", "EM_DISTRIBUICAO", "FECHADO", "CANCELADO")
DISTRIBUTION_STATUSES = ("RASCUNHO", "CONFIRMADA")


class GoalCycle(Base):
    __tablename__ = "goal_cycles"
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_cycle_year_month"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_cycle_month_range"),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in CYCLE_STATUSES)})",
            name="ck_cycle_status_valid",
        ),
        Index("ix_cycles_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[int] = mapped_column(SmallInteger)
    year: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(20), default="RASCUNHO")
    working_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"GoalCycle({self.month:02d}/{self.year})"


# ── SELLER_GOALS: a verdade final (nivel de produto) ───


class SellerGoal(Base):
    """Uma linha por vendedor / produto / ciclo. Dado permanente."""
    __tablename__ = "seller_goals"
    __table_args__ = (
        UniqueConstraint(
            "cycle_id", "product_id", "seller_node_id",
            name="uq_seller_goal",
        ),
        CheckConstraint("quantity_kg > 0", name="ck_seller_goal_qty_positive"),
        Index("ix_sg_cycle", "cycle_id"),
        Index("ix_sg_seller", "seller_node_id"),
        Index("ix_sg_product", "product_id"),
        Index("ix_sg_category", "category_id"),
        Index("ix_sg_cycle_seller", "cycle_id", "seller_node_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("goal_cycles.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    seller_node_id: Mapped[int] = mapped_column(ForeignKey("hierarchy_nodes.id"))
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    cycle: Mapped[GoalCycle] = relationship("GoalCycle")
    category: Mapped["ProductCategory"] = relationship("ProductCategory")  # noqa: F821
    product: Mapped["Product"] = relationship("Product")  # noqa: F821
    seller_node: Mapped["HierarchyNode"] = relationship("HierarchyNode")  # noqa: F821

    def __repr__(self) -> str:
        return f"SellerGoal(seller={self.seller_node_id}, product={self.product_id}, {self.quantity_kg}kg)"


# ── DISTRIBUTIONS: area de trabalho ────────────────────


class Distribution(Base):
    """Rascunho de distribuicao em qualquer nivel.
    - product_id=NULL → distribuicao por GRUPO (Gerente→Regional, Regional→Local)
    - product_id set  → distribuicao por PRODUTO (Local→Supervisor, Supervisor→Vendedor)
    """
    __tablename__ = "distributions"
    __table_args__ = (
        UniqueConstraint(
            "cycle_id", "category_id", "product_id",
            "source_node_id", "destination_node_id",
            name="uq_distribution",
        ),
        CheckConstraint("quantity_kg > 0", name="ck_dist_qty_positive"),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in DISTRIBUTION_STATUSES)})",
            name="ck_dist_status_valid",
        ),
        Index("ix_dist_cycle_source", "cycle_id", "source_node_id"),
        Index("ix_dist_cycle_dest", "cycle_id", "destination_node_id"),
        Index("ix_dist_status", "status"),
        Index("ix_dist_product", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("goal_cycles.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    source_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("hierarchy_nodes.id"), nullable=True
    )
    destination_node_id: Mapped[int] = mapped_column(
        ForeignKey("hierarchy_nodes.id")
    )
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    status: Mapped[str] = mapped_column(String(15), default="RASCUNHO")
    engine_used: Mapped[str] = mapped_column(String(30), default="manual")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    cycle: Mapped[GoalCycle] = relationship("GoalCycle")
    category: Mapped["ProductCategory"] = relationship("ProductCategory")  # noqa: F821
    product: Mapped["Product | None"] = relationship("Product")  # noqa: F821
    source_node: Mapped["HierarchyNode | None"] = relationship(  # noqa: F821
        "HierarchyNode", foreign_keys=[source_node_id]
    )
    destination_node: Mapped["HierarchyNode"] = relationship(  # noqa: F821
        "HierarchyNode", foreign_keys=[destination_node_id]
    )

    def __repr__(self) -> str:
        level = "GRUPO" if self.product_id is None else "PRODUTO"
        return f"Distribution({level}, {self.quantity_kg}kg, {self.status})"


# ── SELLER SUBSTITUTIONS: feristas ─────────────────────


class SellerSubstitution(Base):
    __tablename__ = "seller_substitutions"
    __table_args__ = (
        Index("ix_subs_titular", "titular_node_id"),
        Index("ix_subs_substitute", "substitute_node_id"),
        Index("ix_subs_cycle", "cycle_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titular_node_id: Mapped[int] = mapped_column(ForeignKey("hierarchy_nodes.id"))
    substitute_node_id: Mapped[int] = mapped_column(ForeignKey("hierarchy_nodes.id"))
    cycle_id: Mapped[int] = mapped_column(ForeignKey("goal_cycles.id"))
    starts_on: Mapped[datetime] = mapped_column(Date)
    ends_on: Mapped[datetime] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    titular_node: Mapped["HierarchyNode"] = relationship(  # noqa: F821
        "HierarchyNode", foreign_keys=[titular_node_id]
    )
    substitute_node: Mapped["HierarchyNode"] = relationship(  # noqa: F821
        "HierarchyNode", foreign_keys=[substitute_node_id]
    )
    cycle: Mapped[GoalCycle] = relationship()

    def __repr__(self) -> str:
        return f"SellerSubstitution(titular={self.titular_node_id}, sub={self.substitute_node_id})"


# ── CLIENT TARGETS: meta por cliente ─────────────────


class GoalClientTarget(Base):
    __tablename__ = "goal_client_targets"
    __table_args__ = (
        Index("ix_gct_seller_goal", "seller_goal_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_goal_id: Mapped[int] = mapped_column(ForeignKey("seller_goals.id"))
    client_code: Mapped[str] = mapped_column(String(40))
    client_name: Mapped[str] = mapped_column(String(200), default="")
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(14, 0))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"GoalClientTarget(client={self.client_code!r}, {self.quantity_kg}kg)"
