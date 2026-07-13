from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.goals import SuggestionResult


class CalculationEngine(Protocol):
    display_name: str
    description: str

    async def suggest(
        self,
        db: AsyncSession,
        source_node_id: int,
        cycle_id: int,
        category_id: int,
        product_level: bool = False,
        start_month: str = "",
        end_month: str = "",
    ) -> SuggestionResult: ...
