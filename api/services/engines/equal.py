from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.catalog import Product
from api.models.goals import Distribution
from api.models.hierarchy import HierarchyNode
from api.schemas.goals import SuggestionItem, SuggestionResult


class EqualDistributionEngine:
    display_name = "Distribuicao Igualitaria"
    description = "Distribui igualmente entre todos os filhos ativos"

    async def suggest(
        self,
        db: AsyncSession,
        source_node_id: int,
        cycle_id: int,
        category_id: int,
        product_level: bool = False,
    ) -> SuggestionResult:
        received_result = await db.execute(
            select(Distribution.quantity_kg).where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == category_id,
                Distribution.destination_node_id == source_node_id,
                Distribution.product_id == None,  # noqa: E711
                Distribution.status == "CONFIRMADA",
            )
        )
        received_kg = received_result.scalar_one_or_none() or Decimal("0")
        if received_kg <= 0:
            return SuggestionResult(engine="equal", items=[], total_kg=Decimal("0"))

        children_result = await db.execute(
            select(HierarchyNode)
            .options(selectinload(HierarchyNode.level))
            .where(
                HierarchyNode.parent_id == source_node_id,
                HierarchyNode.is_active == True,  # noqa: E712
            )
            .order_by(HierarchyNode.name)
        )
        children = list(children_result.scalars().all())
        if not children:
            return SuggestionResult(engine="equal", items=[], total_kg=received_kg)

        if product_level:
            products_result = await db.execute(
                select(Product).where(
                    Product.category_id == category_id,
                    Product.is_active == True,  # noqa: E712
                ).order_by(Product.name)
            )
            products = list(products_result.scalars().all())
            if not products:
                return SuggestionResult(engine="equal", items=[], total_kg=received_kg)

            slots = len(children) * len(products)
            base = int(received_kg) // slots
            remainder = int(received_kg) - (base * slots)

            items = []
            i = 0
            for product in products:
                for child in children:
                    suggested = Decimal(str(base + (1 if i < remainder else 0)))
                    pct = (suggested / received_kg * 100) if received_kg else Decimal("0")
                    items.append(SuggestionItem(
                        destination_node_id=child.id,
                        destination_name=child.name,
                        product_id=product.id,
                        product_name=product.name,
                        suggested_kg=suggested,
                        percent=pct,
                    ))
                    i += 1
            return SuggestionResult(engine="equal", items=items, total_kg=received_kg)

        count = len(children)
        base = int(received_kg) // count
        remainder = int(received_kg) - (base * count)
        items = []
        for i, child in enumerate(children):
            suggested = Decimal(str(base + (1 if i < remainder else 0)))
            pct = (suggested / received_kg * 100) if received_kg else Decimal("0")
            items.append(SuggestionItem(
                destination_node_id=child.id,
                destination_name=child.name,
                suggested_kg=suggested,
                percent=pct,
            ))
        return SuggestionResult(engine="equal", items=items, total_kg=received_kg)
