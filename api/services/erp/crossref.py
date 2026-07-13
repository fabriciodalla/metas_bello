"""Cruzamento: clients x accumulated = base_distribution.
Para cada venda no acumulado, troca o vendedor pelo dono do clifor na carteira.
Agrupa por vendedor / produto / mes."""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.portfolio import Accumulated, BaseDistribution, Client
from api.services.erp.normalize import normalize_name


async def build_base_distribution(db: AsyncSession, cycle_id: int) -> dict:
    # 1. Carteira: clifor → (seller_node_id, seller_name)
    clients_result = await db.execute(
        select(Client).where(Client.cycle_id == cycle_id)
    )
    clifor_to_seller: dict[str, tuple[int | None, str]] = {}
    for c in clients_result.scalars().all():
        clifor_to_seller[c.clifor] = (c.seller_node_id, c.seller_name_normalized)

    # 2. Acumulado
    acc_result = await db.execute(
        select(Accumulated).where(Accumulated.cycle_id == cycle_id)
    )
    acc_rows = list(acc_result.scalars().all())

    # 3. Cruzamento: trocar vendedor pelo da carteira, agrupar
    # chave: (seller_node_id, seller_name, product_name, month)
    agg: dict[tuple, Decimal] = defaultdict(Decimal)
    sem_carteira = 0

    for row in acc_rows:
        seller_info = clifor_to_seller.get(row.clifor)
        if not seller_info:
            sem_carteira += 1
            continue

        seller_node_id, seller_name = seller_info
        key = (seller_node_id, seller_name, row.product_name_erp, row.month)
        agg[key] += row.total_kg

    # 4. Limpar base anterior
    await db.execute(
        BaseDistribution.__table__.delete().where(
            BaseDistribution.cycle_id == cycle_id
        )
    )

    # 5. Gravar
    created = 0
    for (seller_node_id, seller_name, product_name, month), total_kg in agg.items():
        db.add(BaseDistribution(
            cycle_id=cycle_id,
            seller_node_id=seller_node_id,
            seller_name=seller_name,
            product_name=product_name,
            month=month,
            total_kg=total_kg,
        ))
        created += 1

    await db.commit()

    return {
        "total_accumulated_rows": len(acc_rows),
        "unmatched_clifor": sem_carteira,
        "base_distribution_rows": created,
    }
