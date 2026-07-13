from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

VALID_ROLES = (
    "ADMINISTRADOR",
    "GERENTE",
    "COORDENADOR_REGIONAL",
    "COORDENADOR_LOCAL",
    "SUPERVISOR",
    "VENDEDOR",
)

from api.models import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            f"role IN ({', '.join(repr(r) for r in VALID_ROLES)})",
            name="ck_user_role_valid",
        ),
        Index("ix_users_role", "role"),
        Index("ix_users_scope_node_id", "scope_node_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(150), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(25), default="VENDEDOR")
    scope_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("hierarchy_nodes.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    scope_node: Mapped["HierarchyNode | None"] = relationship(  # noqa: F821
        "HierarchyNode"
    )

    def __repr__(self) -> str:
        return f"User(username={self.username!r}, role={self.role!r})"
