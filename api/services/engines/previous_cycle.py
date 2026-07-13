from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.catalog import Product
from api.models.goals import Distribution, GoalCycle, SellerGoal
from api.models.hierarchy import HierarchyNode
from api.schemas.goals import SuggestionItem, SuggestionResult


class PreviousCycleEngine:
    display_name = "Ciclo Anterior"
    description = "Distribui proporcionalmente ao ciclo anterior confirmado"

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
            return SuggestionResult(engine="previous_cycle", items=[], total_kg=Decimal("0"))

        cycle = (await db.execute(
            select(GoalCycle).where(GoalCycle.id == cycle_id)
        )).scalar_one_or_none()
        if not cycle:
            return SuggestionResult(engine="previous_cycle", items=[], total_kg=received_kg)

        prev_month = cycle.month - 1
        prev_year = cycle.year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1

        prev_cycle = (await db.execute(
            select(GoalCycle).where(GoalCycle.year == prev_year, GoalCycle.month == prev_month)
        )).scalar_one_or_none()
        if not prev_cycle:
            return SuggestionResult(engine="previous_cycle", items=[], total_kg=received_kg)

        prev_dists = list((await db.execute(
            select(Distribution).where(
                Distribution.cycle_id == prev_cycle.id,
                Distribution.category_id == category_id,
                Distribution.source_node_id == source_node_id,
                Distribution.status == "CONFIRMADA",
            )
        )).scalars().all())

        if not prev_dists:
            return SuggestionResult(engine="previous_cycle", items=[], total_kg=received_kg)

        prev_total = sum(d.quantity_kg for d in prev_dists)
        if prev_total <= 0:
            return SuggestionResult(engine="previous_cycle", items=[], total_kg=received_kg)

        remaining = int(received_kg)
        parts: dict[tuple[int, int | None], int] = {}
        remainders = []
        for d in prev_dists:
            key = (d.destination_node_id, d.product_id)
            exact = (received_kg * d.quantity_kg) / prev_total
            base = int(exact)
            parts[key] = base
            remaining -= base
            remainders.append((exact - base, key))

        remainders.sort(reverse=True)
        for _, key in remainders[:remaining]:
            parts[key] += 1

        dest_ids = {d.destination_node_id for d in prev_dists}
        nodes_by_id = {}
        for node in (await db.execute(
            select(HierarchyNode).options(selectinload(HierarchyNode.level))
            .where(HierarchyNode.id.in_(dest_ids))
        )).scalars().all():
            nodes_by_id[node.id] = node

        prod_ids = {d.product_id for d in prev_dists if d.product_id}
        prods_by_id = {}
        if prod_ids:
            for prod in (await db.execute(
                select(Product).where(Product.id.in_(prod_ids))
            )).scalars().all():
                prods_by_id[prod.id] = prod

        items = []
        for d in prev_dists:
            key = (d.destination_node_id, d.product_id)
            node = nodes_by_id.get(d.destination_node_id)
            prod = prods_by_id.get(d.product_id) if d.product_id else None
            suggested = Decimal(str(parts.get(key, 0)))
            pct = (d.quantity_kg / prev_total * 100) if prev_total else Decimal("0")
            items.append(SuggestionItem(
                destination_node_id=d.destination_node_id,
                destination_name=node.name if node else "",
                product_id=d.product_id,
                product_name=prod.name if prod else "",
                suggested_kg=suggested,
                percent=pct,
            ))

        items.sort(key=lambda x: (x.product_name or "", x.destination_name))
        return SuggestionResult(engine="previous_cycle", items=items, total_kg=received_kg)
