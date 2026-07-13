from decimal import Decimal

from pydantic import BaseModel, field_validator


# ── Cycles ──────────────────────────────────────────────

class GoalCycleRead(BaseModel):
    id: int
    month: int
    year: int
    status: str
    working_days: int | None = None
    total_kg: Decimal = Decimal("0")
    sellers_count: int = 0

    model_config = {"from_attributes": True}


class GoalCycleCreate(BaseModel):
    month: int
    year: int
    working_days: int | None = None

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: int) -> int:
        if v < 1 or v > 12:
            raise ValueError("Mes deve estar entre 1 e 12")
        return v


class GoalCycleUpdate(BaseModel):
    status: str | None = None
    working_days: int | None = None


# ── Seller Goals (verdade final, nivel produto) ─────────

class SellerGoalRead(BaseModel):
    id: int
    cycle_id: int
    cycle_label: str = ""
    category_id: int
    category_name: str = ""
    product_id: int
    product_name: str = ""
    seller_node_id: int
    seller_name: str = ""
    quantity_kg: Decimal
    notes: str = ""

    model_config = {"from_attributes": True}


class SellerGoalSummary(BaseModel):
    node_id: int
    node_name: str
    node_level: str
    category_id: int
    category_name: str
    total_kg: Decimal
    sellers_count: int
    products_count: int = 0


# ── Distributions (area de trabalho) ────────────────────

class DistributionRead(BaseModel):
    id: int
    cycle_id: int
    category_id: int
    category_name: str = ""
    product_id: int | None = None
    product_name: str = ""
    source_node_id: int | None
    source_name: str = ""
    destination_node_id: int
    destination_name: str = ""
    destination_level: str = ""
    quantity_kg: Decimal
    status: str
    engine_used: str = "manual"

    model_config = {"from_attributes": True}


class DistributionCreate(BaseModel):
    destination_node_id: int
    quantity_kg: Decimal
    product_id: int | None = None

    @field_validator("quantity_kg")
    @classmethod
    def validate_qty(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return v


class BulkDistributionItem(BaseModel):
    destination_node_id: int
    quantity_kg: Decimal
    product_id: int | None = None


class BulkDistributionCreate(BaseModel):
    items: list[BulkDistributionItem]


class WorkspaceRead(BaseModel):
    source_node_id: int
    source_name: str
    source_level: str = ""
    category_id: int
    category_name: str = ""
    received_kg: Decimal
    distributed_kg: Decimal
    remaining_kg: Decimal
    can_confirm: bool
    is_product_level: bool = False
    items: list[DistributionRead] = []


# ── Suggestions ─────────────────────────────────────────

class SuggestionItem(BaseModel):
    destination_node_id: int
    destination_name: str
    product_id: int | None = None
    product_name: str = ""
    suggested_kg: Decimal
    percent: Decimal


class SuggestionResult(BaseModel):
    engine: str
    items: list[SuggestionItem]
    total_kg: Decimal


class SuggestionRequest(BaseModel):
    engine: str = "portfolio"
    start_month: str = ""
    end_month: str = ""


# ── Client Targets ──────────────────────────────────────

class ClientTargetRead(BaseModel):
    id: int
    seller_goal_id: int
    client_code: str
    client_name: str
    quantity_kg: Decimal

    model_config = {"from_attributes": True}


class ClientTargetCreate(BaseModel):
    client_code: str
    client_name: str = ""
    quantity_kg: Decimal


# ── Substitutions ───────────────────────────────────────

class SubstitutionRead(BaseModel):
    id: int
    titular_node_id: int
    titular_name: str = ""
    substitute_node_id: int
    substitute_name: str = ""
    cycle_id: int
    starts_on: str
    ends_on: str
    notes: str = ""

    model_config = {"from_attributes": True}


class SubstitutionCreate(BaseModel):
    titular_node_id: int
    substitute_node_id: int
    cycle_id: int
    starts_on: str
    ends_on: str
    notes: str = ""
