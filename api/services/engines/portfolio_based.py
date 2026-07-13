"""Engine principal: cruza carteira (snapshot local) com acumulado (ERP)
para gerar sugestao de distribuicao baseada no vendedor ATUAL de cada cliente."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_FLOOR

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.catalog import Product
from api.models.goals import Distribution
from api.models.hierarchy import HierarchyNode
from api.models.portfolio import ClientPortfolio
from api.schemas.goals import SuggestionItem, SuggestionResult
from api.services.erp.normalize import normalize_name
from api.services.erp.sales_history import fetch_sales_history

KG = Decimal("1")


class PortfolioBasedEngine:
    display_name = "Carteira + Historico"
    description = "Cruza carteira atual com historico de vendas. Vendedor = dono do cliente hoje."

    async def suggest(
        self,
        db: AsyncSession,
        source_node_id: int,
        cycle_id: int,
        category_id: int,
        product_level: bool = False,
        start_month: str = "",
        end_month: str = "",
    ) -> SuggestionResult:
        # 1. Quanto o source recebeu
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
            return SuggestionResult(engine="portfolio", items=[], total_kg=Decimal("0"))

        # 2. Carteira snapshot (já no banco local, vinculada ao ciclo)
        portfolio_result = await db.execute(
            select(ClientPortfolio).where(ClientPortfolio.cycle_id == cycle_id)
        )
        portfolio = list(portfolio_result.scalars().all())
        if not portfolio:
            return SuggestionResult(engine="portfolio", items=[], total_kg=received_kg)

        # clifor → seller_node_id (da carteira)
        clifor_to_seller: dict[str, int | None] = {}
        for p in portfolio:
            if p.seller_node_id:
                clifor_to_seller[p.clifor] = p.seller_node_id

        # 3. Filhos do source (destinos possíveis)
        children_result = await db.execute(
            select(HierarchyNode)
            .options(selectinload(HierarchyNode.level))
            .where(
                HierarchyNode.parent_id == source_node_id,
                HierarchyNode.is_active == True,  # noqa: E712
            )
        )
        children = list(children_result.scalars().all())
        if not children:
            return SuggestionResult(engine="portfolio", items=[], total_kg=received_kg)

        # Coletar todos os vendedores abaixo de cada filho
        child_seller_ids: dict[int, set[int]] = {}
        for child in children:
            sellers = await _get_all_sellers_below(db, child.id)
            child_seller_ids[child.id] = {s.id for s in sellers}
            child_seller_ids[child.id].add(child.id)

        # 4. Produtos da categoria
        products_by_name: dict[str, Product] = {}
        if product_level:
            prods_result = await db.execute(
                select(Product).where(
                    Product.category_id == category_id,
                    Product.is_active == True,  # noqa: E712
                )
            )
            for p in prods_result.scalars().all():
                products_by_name[normalize_name(p.name)] = p

        # 5. Buscar acumulado do ERP
        if not start_month or not end_month:
            return SuggestionResult(engine="portfolio", items=[], total_kg=received_kg)

        history = fetch_sales_history(start_month, end_month)

        # 6. CRUZAMENTO: para cada venda, trocar vendedor pelo dono do clifor
        if product_level:
            # Agregar por (child_id, product_id)
            agg: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
        else:
            # Agregar por child_id
            agg: dict[tuple[int, None], Decimal] = defaultdict(Decimal)

        unmatched_kg = Decimal("0")

        for sale in history:
            seller_node_id = clifor_to_seller.get(sale.clifor)
            if not seller_node_id:
                unmatched_kg += sale.total_kg
                continue

            # Achar qual filho do source contém esse seller
            target_child_id = None
            for child in children:
                if seller_node_id in child_seller_ids[child.id]:
                    target_child_id = child.id
                    break

            if not target_child_id:
                unmatched_kg += sale.total_kg
                continue

            if product_level:
                prod = products_by_name.get(normalize_name(sale.subgroup_name))
                if not prod:
                    unmatched_kg += sale.total_kg
                    continue
                agg[(target_child_id, prod.id)] += sale.total_kg
            else:
                agg[(target_child_id, None)] += sale.total_kg

        if not agg:
            return SuggestionResult(engine="portfolio", items=[], total_kg=received_kg)

        # 7. Calcular proporção e distribuir received_kg
        total_historical = sum(agg.values())
        if total_historical <= 0:
            return SuggestionResult(engine="portfolio", items=[], total_kg=received_kg)

        suggested = _proportional_allocation(received_kg, agg)

        # 8. Montar resultado
        children_by_id = {c.id: c for c in children}
        products_by_id: dict[int, Product] = {}
        if product_level:
            prod_ids = {k[1] for k in agg if k[1]}
            if prod_ids:
                prods = await db.execute(
                    select(Product).where(Product.id.in_(prod_ids))
                )
                products_by_id = {p.id: p for p in prods.scalars().all()}

        items = []
        for (child_id, prod_id), hist_kg in sorted(agg.items(), key=lambda x: x[1], reverse=True):
            child = children_by_id.get(child_id)
            prod = products_by_id.get(prod_id) if prod_id else None
            sugg_kg = suggested.get((child_id, prod_id), Decimal("0"))
            pct = (hist_kg / total_historical * 100) if total_historical else Decimal("0")

            items.append(SuggestionItem(
                destination_node_id=child_id,
                destination_name=child.name if child else "",
                product_id=prod_id,
                product_name=prod.name if prod else "",
                suggested_kg=sugg_kg,
                percent=pct,
            ))

        return SuggestionResult(engine="portfolio", items=items, total_kg=received_kg)


def _proportional_allocation(
    target_kg: Decimal,
    historical: dict[tuple[int, int | None], Decimal],
) -> dict[tuple[int, int | None], Decimal]:
    total = sum(historical.values())
    if total <= 0:
        return {}

    parts: dict[tuple[int, int | None], Decimal] = {}
    remaining = int(target_kg)
    remainders = []

    for key, hist_kg in historical.items():
        exact = (target_kg * hist_kg) / total
        base = int(exact)
        parts[key] = Decimal(str(base))
        remaining -= base
        remainders.append((exact - base, key))

    remainders.sort(reverse=True)
    for _, key in remainders[:remaining]:
        parts[key] += KG

    return parts


async def _get_all_sellers_below(db: AsyncSession, node_id: int) -> list[HierarchyNode]:
    from api.models.hierarchy import HierarchyLevel
    seller_level = (await db.execute(
        select(HierarchyLevel.id).order_by(HierarchyLevel.depth.desc()).limit(1)
    )).scalar()

    sellers = []
    queue = [node_id]
    visited = set()
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        children = await db.execute(
            select(HierarchyNode).where(
                HierarchyNode.parent_id == current,
                HierarchyNode.is_active == True,  # noqa: E712
            )
        )
        for child in children.scalars().all():
            if child.level_id == seller_level:
                sellers.append(child)
            else:
                queue.append(child.id)
    return sellers
