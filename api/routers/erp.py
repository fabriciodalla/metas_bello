from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.accounts import User
from api.models.goals import GoalCycle
from api.models.hierarchy import HierarchyNode
from api.models.portfolio import Accumulated, BaseDistribution, Client
from api.routers.auth import get_current_user
from api.services.erp.connection import ErpConfigError, ErpQueryError
from api.services.erp.normalize import normalize_name
from api.services.erp.portfolio import fetch_portfolio
from api.services.erp.sales_history import fetch_accumulated

router = APIRouter(prefix="/erp", tags=["erp"])


class SyncResult(BaseModel):
    total_rows: int
    matched: int
    unmatched: int
    unmatched_names: list[str] = []


# ── 1. Sync Carteira → tabela clients ──────────────────

@router.post("/clients/sync/{cycle_id}", response_model=SyncResult)
async def sync_clients(
    cycle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulta ERP e grava snapshot da carteira para o ciclo."""
    cycle = (await db.execute(
        select(GoalCycle).where(GoalCycle.id == cycle_id)
    )).scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")

    try:
        rows = fetch_portfolio()
    except (ErpConfigError, ErpQueryError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    await db.execute(Client.__table__.delete().where(Client.cycle_id == cycle_id))

    nodes_result = await db.execute(select(HierarchyNode))
    nodes_by_name: dict[str, HierarchyNode] = {}
    for node in nodes_result.scalars().all():
        nodes_by_name[normalize_name(node.name)] = node

    matched, unmatched = 0, 0
    unmatched_names: set[str] = set()

    for row in rows:
        node = nodes_by_name.get(row.seller_name_normalized)
        db.add(Client(
            cycle_id=cycle_id, clifor=row.clifor, cnpj=row.cnpj,
            client_name=row.client_name, seller_name_erp=row.seller_name,
            seller_name_normalized=row.seller_name_normalized,
            supervisor_code_erp=row.supervisor_code,
            municipality=row.municipality, state=row.state,
            seller_node_id=node.id if node else None,
        ))
        if node:
            matched += 1
        else:
            unmatched += 1
            unmatched_names.add(row.seller_name_normalized)

    await db.commit()
    return SyncResult(
        total_rows=len(rows), matched=matched, unmatched=unmatched,
        unmatched_names=sorted(unmatched_names),
    )


# ── 2. Sync Acumulado → tabela accumulated ─────────────

@router.post("/accumulated/sync/{cycle_id}", response_model=SyncResult)
async def sync_accumulated(
    cycle_id: int,
    start_date: str = "2026-01-01",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulta ERP e grava historico de vendas para o ciclo."""
    cycle = (await db.execute(
        select(GoalCycle).where(GoalCycle.id == cycle_id)
    )).scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")

    try:
        rows = fetch_accumulated(start_date)
    except (ErpConfigError, ErpQueryError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    await db.execute(Accumulated.__table__.delete().where(Accumulated.cycle_id == cycle_id))

    for row in rows:
        db.add(Accumulated(
            cycle_id=cycle_id, supervisor_code_erp=row.supervisor_code,
            seller_code_erp=row.seller_code, seller_name_erp=row.seller_name,
            seller_name_normalized=row.seller_name_normalized,
            clifor=row.clifor, cnpj=row.cnpj, client_name=row.client_name,
            month=row.month, product_name_erp=row.product_name,
            product_name_normalized=row.product_name_normalized,
            total_kg=row.total_kg, total_value=row.total_value,
            company_code_erp=row.company_code,
        ))

    await db.commit()
    return SyncResult(total_rows=len(rows), matched=len(rows), unmatched=0)


# ── 3. Cruzamento → tabela base_distribution ───────────

class CrossRefResult(BaseModel):
    total_accumulated_rows: int
    unmatched_clifor: int
    unmatched_product: int = 0
    base_distribution_rows: int


@router.post("/base-distribution/build/{cycle_id}", response_model=CrossRefResult)
async def build_base(
    cycle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cruza clients x accumulated, troca vendedor pelo da carteira, grava base_distribution."""
    from api.services.erp.crossref import build_base_distribution
    result = await build_base_distribution(db, cycle_id)
    return CrossRefResult(**result)


# ── Stats ───────────────────────────────────────────────

class TableStats(BaseModel):
    cycle_id: int
    clients: int
    accumulated: int
    base_distribution: int
    sellers_matched: int


@router.get("/stats/{cycle_id}", response_model=TableStats)
async def erp_stats(cycle_id: int, db: AsyncSession = Depends(get_db)):
    clients = (await db.execute(
        select(func.count(Client.id)).where(Client.cycle_id == cycle_id)
    )).scalar() or 0
    accumulated = (await db.execute(
        select(func.count(Accumulated.id)).where(Accumulated.cycle_id == cycle_id)
    )).scalar() or 0
    base = (await db.execute(
        select(func.count(BaseDistribution.id)).where(BaseDistribution.cycle_id == cycle_id)
    )).scalar() or 0
    sellers = (await db.execute(
        select(func.count(func.distinct(Client.seller_node_id))).where(
            Client.cycle_id == cycle_id, Client.seller_node_id != None,  # noqa: E711
        )
    )).scalar() or 0

    return TableStats(
        cycle_id=cycle_id, clients=clients, accumulated=accumulated,
        base_distribution=base, sellers_matched=sellers,
    )
