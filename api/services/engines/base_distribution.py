"""Motor de distribuição proporcional baseado na tabela base_distribution.

Calcula a meta individual de cada nó filho usando a média diária dos
últimos 3 meses (soma / dias úteis) × dias úteis do mês alvo.
Distribui a meta recebida proporcionalmente entre os filhos.
Sobra de arredondamento é redistribuída pelo método do maior resto.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import and_, extract, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.catalog import Product
from api.models.goals import Distribution, GoalCycle
from api.models.hierarchy import HierarchyNode
from api.models.portfolio import BaseDistribution
from api.schemas.goals import SuggestionItem, SuggestionResult
from api.services.erp.normalize import normalize_name
from api.services.working_days import get_effective_working_days, previous_months

KG = Decimal("1")


class BaseDistributionEngine:
    display_name = "Distribuição Proporcional (Base)"
    description = (
        "Média diária dos últimos 3 meses × dias úteis do mês alvo. "
        "Distribui proporcionalmente a meta recebida."
    )

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
        engine_name = "base_distribution"

        cycle = (await db.execute(
            select(GoalCycle).where(GoalCycle.id == cycle_id)
        )).scalar_one_or_none()
        if not cycle:
            return SuggestionResult(engine=engine_name, items=[], total_kg=Decimal("0"))

        # ── Meta recebida de cima (distribution confirmada para este nó) ──
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

        # ── Dias úteis (considera feriados + override do admin) ─────────
        target_wd = await get_effective_working_days(db, cycle.year, cycle.month)

        prev_months_list = previous_months(cycle.year, cycle.month, 3)
        prev_wd = 0
        for py, pm in prev_months_list:
            prev_wd += await get_effective_working_days(db, py, pm)
        if prev_wd <= 0:
            prev_wd = 1

        # ── Filhos ativos do nó ───────────────────────────────────────────
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
            total = received_kg if received_kg > 0 else Decimal("0")
            return SuggestionResult(engine=engine_name, items=[], total_kg=total)

        # ── Descendentes de cada filho (para mapear seller → child) ───────
        child_descendants: dict[int, set[int]] = {}
        for child in children:
            child_descendants[child.id] = await _get_all_descendants(db, child.id)

        # ── Produtos da categoria ─────────────────────────────────────────
        prods_result = await db.execute(
            select(Product).where(
                Product.category_id == category_id,
                Product.is_active == True,  # noqa: E712
            )
        )
        products = list(prods_result.scalars().all())
        products_by_norm: dict[str, Product] = {
            normalize_name(p.name): p for p in products
        }

        # ── Base distribution dos 3 meses anteriores ─────────────────────
        month_filters = [
            and_(
                extract("year", BaseDistribution.month) == py,
                extract("month", BaseDistribution.month) == pm,
            )
            for py, pm in prev_months_list
        ]
        base_result = await db.execute(
            select(BaseDistribution).where(
                BaseDistribution.cycle_id == cycle_id,
                or_(*month_filters),
            )
        )
        base_rows = list(base_result.scalars().all())

        if not base_rows:
            total = received_kg if received_kg > 0 else Decimal("0")
            return SuggestionResult(engine=engine_name, items=[], total_kg=total)

        # ── Agregar vendas por (child_id, product_id | None) ─────────────
        agg_sales: dict[tuple[int, int | None], Decimal] = defaultdict(Decimal)

        for row in base_rows:
            if not row.seller_node_id:
                continue

            prod = products_by_norm.get(normalize_name(row.product_name))
            if not prod:
                continue

            target_child_id = None
            for child in children:
                if row.seller_node_id in child_descendants[child.id]:
                    target_child_id = child.id
                    break
            if not target_child_id:
                continue

            if product_level:
                agg_sales[(target_child_id, prod.id)] += row.total_kg
            else:
                agg_sales[(target_child_id, None)] += row.total_kg

        if not agg_sales:
            total = received_kg if received_kg > 0 else Decimal("0")
            return SuggestionResult(engine=engine_name, items=[], total_kg=total)

        # ── Meta individual: (soma_3m / dias_uteis_3m) × dias_uteis_alvo ─
        individual_targets: dict[tuple[int, int | None], Decimal] = {}
        for key, sum_3m in agg_sales.items():
            daily_avg = sum_3m / Decimal(str(prev_wd))
            individual = (daily_avg * Decimal(str(target_wd))).quantize(KG)
            individual_targets[key] = individual

        total_individual = sum(individual_targets.values())
        if total_individual <= 0:
            total = received_kg if received_kg > 0 else Decimal("0")
            return SuggestionResult(engine=engine_name, items=[], total_kg=total)

        # ── Definir orçamento a distribuir ────────────────────────────────
        # Se há meta recebida de cima, distribui ela proporcionalmente.
        # Se não (nível gerencial), sugere a soma das metas individuais.
        has_budget = received_kg > 0
        budget = received_kg if has_budget else total_individual

        # ── Alocação proporcional (maior resto garante 100%) ─────────────
        allocated = _proportional_allocation(budget, individual_targets)

        # ── Montar resultado ──────────────────────────────────────────────
        children_by_id = {c.id: c for c in children}
        products_by_id = {p.id: p for p in products}

        items = []
        for key in sorted(
            agg_sales.keys(),
            key=lambda k: individual_targets.get(k, Decimal("0")),
            reverse=True,
        ):
            child_id, prod_id = key
            child = children_by_id.get(child_id)
            prod = products_by_id.get(prod_id) if prod_id else None
            sugg_kg = allocated.get(key, Decimal("0"))
            indiv = individual_targets.get(key, Decimal("0"))
            pct = (indiv / total_individual * 100) if total_individual else Decimal("0")

            items.append(SuggestionItem(
                destination_node_id=child_id,
                destination_name=child.name if child else "",
                product_id=prod_id,
                product_name=prod.name if prod else "",
                suggested_kg=sugg_kg,
                percent=pct,
            ))

        return SuggestionResult(
            engine=engine_name,
            items=items,
            total_kg=budget,
        )


def _proportional_allocation(
    target_kg: Decimal,
    shares: dict[tuple[int, int | None], Decimal],
) -> dict[tuple[int, int | None], Decimal]:
    """Distribui target_kg proporcionalmente. Maior resto redistribui a sobra."""
    total = sum(shares.values())
    if total <= 0:
        return {}

    parts: dict[tuple[int, int | None], Decimal] = {}
    budget = int(target_kg)
    allocated_sum = 0
    remainders: list[tuple[Decimal, tuple[int, int | None]]] = []

    for key, share in shares.items():
        exact = (target_kg * share) / total
        base = int(exact)
        parts[key] = Decimal(str(base))
        allocated_sum += base
        remainders.append((exact - base, key))

    remaining = budget - allocated_sum
    remainders.sort(reverse=True)
    for _, key in remainders[:remaining]:
        parts[key] += KG

    return parts


async def _get_all_descendants(db: AsyncSession, node_id: int) -> set[int]:
    """Retorna todos os IDs de nós abaixo de node_id (inclusive)."""
    result = {node_id}
    queue = [node_id]
    while queue:
        current = queue.pop(0)
        children = await db.execute(
            select(HierarchyNode.id).where(
                HierarchyNode.parent_id == current,
                HierarchyNode.is_active == True,  # noqa: E712
            )
        )
        for (child_id,) in children.all():
            if child_id not in result:
                result.add(child_id)
                queue.append(child_id)
    return result
