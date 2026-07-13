from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models import Base


class HierarchyLevel(Base):
    __tablename__ = "hierarchy_levels"
    __table_args__ = (
        CheckConstraint("depth >= 1 AND depth <= 20", name="ck_level_depth_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    depth: Mapped[int] = mapped_column(SmallInteger, unique=True)
    prefix: Mapped[str] = mapped_column(String(5), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    nodes: Mapped[list["HierarchyNode"]] = relationship(back_populates="level")

    def __repr__(self) -> str:
        return f"HierarchyLevel(depth={self.depth}, name={self.name!r})"


class HierarchyNode(Base):
    __tablename__ = "hierarchy_nodes"
    __table_args__ = (
        Index("ix_nodes_parent_id", "parent_id"),
        Index("ix_nodes_level_id", "level_id"),
        Index("ix_nodes_active_level", "is_active", "level_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level_id: Mapped[int] = mapped_column(ForeignKey("hierarchy_levels.id"))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("hierarchy_nodes.id"), nullable=True
    )
    source_id: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    level: Mapped[HierarchyLevel] = relationship(back_populates="nodes")
    parent: Mapped["HierarchyNode | None"] = relationship(
        remote_side="HierarchyNode.id", back_populates="children"
    )
    children: Mapped[list["HierarchyNode"]] = relationship(back_populates="parent")
    events: Mapped[list["HierarchyEvent"]] = relationship(
        back_populates="node", foreign_keys="HierarchyEvent.node_id"
    )

    def __repr__(self) -> str:
        return f"HierarchyNode(source_id={self.source_id!r}, name={self.name!r})"


HIERARCHY_EVENT_TYPES = (
    "ENTRADA",
    "SAIDA",
    "TRANSFERENCIA",
    "INATIVACAO",
    "REATIVACAO",
)


class HierarchyEvent(Base):
    __tablename__ = "hierarchy_events"
    __table_args__ = (
        CheckConstraint(
            f"event_type IN ({', '.join(repr(e) for e in HIERARCHY_EVENT_TYPES)})",
            name="ck_hier_event_type_valid",
        ),
        Index("ix_hier_events_node_id", "node_id"),
        Index("ix_hier_events_effective_on", "effective_on"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("hierarchy_nodes.id"))
    event_type: Mapped[str] = mapped_column(String(20))
    old_parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("hierarchy_nodes.id"), nullable=True
    )
    new_parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("hierarchy_nodes.id"), nullable=True
    )
    effective_on: Mapped[datetime] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    node: Mapped[HierarchyNode] = relationship(
        foreign_keys=[node_id], back_populates="events"
    )
    old_parent: Mapped[HierarchyNode | None] = relationship(foreign_keys=[old_parent_id])
    new_parent: Mapped[HierarchyNode | None] = relationship(foreign_keys=[new_parent_id])

    def __repr__(self) -> str:
        return f"HierarchyEvent({self.event_type}, node={self.node_id})"
