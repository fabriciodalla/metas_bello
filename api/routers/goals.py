from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database import get_db
from api.models.accounts import User
from api.models.catalog import Product, ProductCategory
from api.models.goals import (
    Distribution,
    GoalClientTarget,
    GoalCycle,
    SellerGoal,
    SellerSubstitution,
)
from api.models.hierarchy import HierarchyLevel, HierarchyNode
from api.routers.auth import get_current_user
from api.schemas.goals import (
    BulkDistributionCreate,
    ClientTargetCreate,
    ClientTargetRead,
    DistributionCreate,
    DistributionRead,
    GoalCycleCreate,
    GoalCycleRead,
    GoalCycleUpdate,
    SellerGoalRead,
    SellerGoalSummary,
    SubstitutionCreate,
    SubstitutionRead,
    SuggestionRequest,
    SuggestionResult,
    WorkspaceRead,
)

router = APIRouter(prefix="/goals", tags=["goals"])


# ── helpers ─────────────────────────────────────────────

async def _node_with_level(db: AsyncSession, node_id: int) -> HierarchyNode | None:
    r = await db.execute(
        select(HierarchyNode).options(selectinload(HierarchyNode.level))
        .where(HierarchyNode.id == node_id)
    )
    return r.scalar_one_or_none()


async def _is_product_level(db: AsyncSession, source_node_id: int) -> bool:
    """Coordenador Local (depth=3) e abaixo distribuem por produto."""
    node = await _node_with_level(db, source_node_id)
    if not node or not node.level:
        return False
    return node.level.depth >= 3


async def _seller_level_id(db: AsyncSession) -> int | None:
    r = await db.execute(
        select(HierarchyLevel.id).order_by(HierarchyLevel.depth.desc()).limit(1)
    )
    return r.scalar()


async def _build_dist_read(dist: Distribution, db: AsyncSession) -> DistributionRead:
    cat_name = (await db.execute(
        select(ProductCategory.name).where(ProductCategory.id == dist.category_id)
    )).scalar() or ""

    prod_name = ""
    if dist.product_id:
        prod_name = (await db.execute(
            select(Product.name).where(Product.id == dist.product_id)
        )).scalar() or ""

    dest = await _node_with_level(db, dist.destination_node_id)
    src_name = ""
    if dist.source_node_id:
        src_name = (await db.execute(
            select(HierarchyNode.name).where(HierarchyNode.id == dist.source_node_id)
        )).scalar() or ""

    return DistributionRead(
        id=dist.id,
        cycle_id=dist.cycle_id,
        category_id=dist.category_id,
        category_name=cat_name,
        product_id=dist.product_id,
        product_name=prod_name,
        source_node_id=dist.source_node_id,
        source_name=src_name,
        destination_node_id=dist.destination_node_id,
        destination_name=dest.name if dest else "",
        destination_level=dest.level.name if dest and dest.level else "",
        quantity_kg=dist.quantity_kg,
        status=dist.status,
        engine_used=dist.engine_used,
    )


async def _get_seller_descendants(db: AsyncSession, node_id: int) -> list[HierarchyNode]:
    slid = await _seller_level_id(db)
    if not slid:
        return []
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
            if child.level_id == slid:
                sellers.append(child)
            else:
                queue.append(child.id)
    return sellers


# ── Cycles ──────────────────────────────────────────────

@router.get("/cycles", response_model=list[GoalCycleRead])
async def list_cycles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GoalCycle).order_by(GoalCycle.year.desc(), GoalCycle.month.desc())
    )
    out = []
    for cycle in result.scalars().all():
        stats = await db.execute(
            select(
                func.coalesce(func.sum(SellerGoal.quantity_kg), 0),
                func.count(SellerGoal.id),
            ).where(SellerGoal.cycle_id == cycle.id)
        )
        total_kg, sellers_count = stats.one()
        read = GoalCycleRead.model_validate(cycle)
        read.total_kg = total_kg
        read.sellers_count = sellers_count
        out.append(read)
    return out


@router.post("/cycles", response_model=GoalCycleRead, status_code=201)
async def create_cycle(
    body: GoalCycleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(GoalCycle).where(GoalCycle.year == body.year, GoalCycle.month == body.month)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ciclo ja existe")
    cycle = GoalCycle(
        month=body.month, year=body.year,
        working_days=body.working_days, created_by_id=current_user.id,
    )
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)
    return GoalCycleRead.model_validate(cycle)


@router.get("/cycles/{cycle_id}", response_model=GoalCycleRead)
async def get_cycle(cycle_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(GoalCycle).where(GoalCycle.id == cycle_id))
    cycle = r.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")
    return GoalCycleRead.model_validate(cycle)


@router.patch("/cycles/{cycle_id}", response_model=GoalCycleRead)
async def update_cycle(
    cycle_id: int, body: GoalCycleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = await db.execute(select(GoalCycle).where(GoalCycle.id == cycle_id))
    cycle = r.scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(cycle, k, v)
    await db.commit()
    await db.refresh(cycle)
    return GoalCycleRead.model_validate(cycle)


# ── Seller Goals (verdade final) ────────────────────────

@router.get("/seller-goals", response_model=list[SellerGoalRead])
async def list_seller_goals(
    cycle_id: int,
    category_id: int | None = None,
    seller_node_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(SellerGoal).where(SellerGoal.cycle_id == cycle_id)
    if category_id:
        query = query.where(SellerGoal.category_id == category_id)
    if seller_node_id:
        query = query.where(SellerGoal.seller_node_id == seller_node_id)
    result = await db.execute(query.order_by(SellerGoal.id))

    out = []
    for sg in result.scalars().all():
        cat_name = (await db.execute(
            select(ProductCategory.name).where(ProductCategory.id == sg.category_id)
        )).scalar() or ""
        prod_name = (await db.execute(
            select(Product.name).where(Product.id == sg.product_id)
        )).scalar() or ""
        seller_name = (await db.execute(
            select(HierarchyNode.name).where(HierarchyNode.id == sg.seller_node_id)
        )).scalar() or ""
        c = (await db.execute(select(GoalCycle).where(GoalCycle.id == sg.cycle_id))).scalar_one_or_none()
        out.append(SellerGoalRead(
            id=sg.id, cycle_id=sg.cycle_id,
            cycle_label=f"{c.month:02d}/{c.year}" if c else "",
            category_id=sg.category_id, category_name=cat_name,
            product_id=sg.product_id, product_name=prod_name,
            seller_node_id=sg.seller_node_id, seller_name=seller_name,
            quantity_kg=sg.quantity_kg, notes=sg.notes,
        ))
    return out


@router.get("/seller-goals/summary", response_model=list[SellerGoalSummary])
async def seller_goals_summary(
    cycle_id: int, node_id: int,
    db: AsyncSession = Depends(get_db),
):
    descendants = await _get_seller_descendants(db, node_id)
    seller_ids = [s.id for s in descendants]
    if not seller_ids:
        return []

    result = await db.execute(
        select(
            SellerGoal.category_id,
            func.sum(SellerGoal.quantity_kg),
            func.count(SellerGoal.id),
            func.count(func.distinct(SellerGoal.product_id)),
        )
        .where(SellerGoal.cycle_id == cycle_id, SellerGoal.seller_node_id.in_(seller_ids))
        .group_by(SellerGoal.category_id)
    )
    node = await _node_with_level(db, node_id)
    out = []
    for cat_id, total, count, prod_count in result.all():
        cat_name = (await db.execute(
            select(ProductCategory.name).where(ProductCategory.id == cat_id)
        )).scalar() or ""
        out.append(SellerGoalSummary(
            node_id=node_id,
            node_name=node.name if node else "",
            node_level=node.level.name if node and node.level else "",
            category_id=cat_id, category_name=cat_name,
            total_kg=total, sellers_count=count, products_count=prod_count,
        ))
    return out


# ── Workspace (area de trabalho) ────────────────────────

@router.get("/workspace", response_model=WorkspaceRead)
async def get_workspace(
    cycle_id: int, category_id: int, source_node_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product_level = await _is_product_level(db, source_node_id)

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

    if product_level:
        items_result = await db.execute(
            select(Distribution).where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == category_id,
                Distribution.source_node_id == source_node_id,
                Distribution.product_id != None,  # noqa: E711
            ).order_by(Distribution.product_id, Distribution.destination_node_id)
        )
    else:
        items_result = await db.execute(
            select(Distribution).where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == category_id,
                Distribution.source_node_id == source_node_id,
                Distribution.product_id == None,  # noqa: E711
            ).order_by(Distribution.destination_node_id)
        )

    items = list(items_result.scalars().all())
    distributed_kg = sum(d.quantity_kg for d in items)
    remaining = received_kg - distributed_kg
    node = await _node_with_level(db, source_node_id)
    cat_name = (await db.execute(
        select(ProductCategory.name).where(ProductCategory.id == category_id)
    )).scalar() or ""

    return WorkspaceRead(
        source_node_id=source_node_id,
        source_name=node.name if node else "",
        source_level=node.level.name if node and node.level else "",
        category_id=category_id,
        category_name=cat_name,
        received_kg=received_kg,
        distributed_kg=distributed_kg,
        remaining_kg=remaining,
        can_confirm=remaining == Decimal("0") and len(items) > 0,
        is_product_level=product_level,
        items=[await _build_dist_read(d, db) for d in items],
    )


@router.post(
    "/workspace/{cycle_id}/{category_id}/{source_node_id}/distribute",
    response_model=DistributionRead, status_code=201,
)
async def add_distribution(
    cycle_id: int, category_id: int, source_node_id: int,
    body: DistributionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product_level = await _is_product_level(db, source_node_id)
    product_id = body.product_id if product_level else None

    dist = Distribution(
        cycle_id=cycle_id, category_id=category_id,
        product_id=product_id,
        source_node_id=source_node_id,
        destination_node_id=body.destination_node_id,
        quantity_kg=body.quantity_kg,
        created_by_id=current_user.id,
    )
    db.add(dist)
    await db.commit()
    await db.refresh(dist)
    return await _build_dist_read(dist, db)


@router.put(
    "/workspace/{cycle_id}/{category_id}/{source_node_id}/bulk",
    response_model=WorkspaceRead,
)
async def bulk_distribute(
    cycle_id: int, category_id: int, source_node_id: int,
    body: BulkDistributionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product_level = await _is_product_level(db, source_node_id)

    if product_level:
        await db.execute(
            Distribution.__table__.delete().where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == category_id,
                Distribution.source_node_id == source_node_id,
                Distribution.product_id != None,  # noqa: E711
                Distribution.status == "RASCUNHO",
            )
        )
    else:
        await db.execute(
            Distribution.__table__.delete().where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == category_id,
                Distribution.source_node_id == source_node_id,
                Distribution.product_id == None,  # noqa: E711
                Distribution.status == "RASCUNHO",
            )
        )

    for item in body.items:
        pid = item.product_id if product_level else None
        db.add(Distribution(
            cycle_id=cycle_id, category_id=category_id,
            product_id=pid,
            source_node_id=source_node_id,
            destination_node_id=item.destination_node_id,
            quantity_kg=item.quantity_kg,
            created_by_id=current_user.id,
        ))
    await db.commit()
    return await get_workspace(cycle_id, category_id, source_node_id, db, current_user)


@router.post("/workspace/{cycle_id}/{category_id}/{source_node_id}/confirm")
async def confirm_distributions(
    cycle_id: int, category_id: int, source_node_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product_level = await _is_product_level(db, source_node_id)

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

    if product_level:
        drafts_q = select(Distribution).where(
            Distribution.cycle_id == cycle_id,
            Distribution.category_id == category_id,
            Distribution.source_node_id == source_node_id,
            Distribution.product_id != None,  # noqa: E711
            Distribution.status == "RASCUNHO",
        )
    else:
        drafts_q = select(Distribution).where(
            Distribution.cycle_id == cycle_id,
            Distribution.category_id == category_id,
            Distribution.source_node_id == source_node_id,
            Distribution.product_id == None,  # noqa: E711
            Distribution.status == "RASCUNHO",
        )

    drafts = list((await db.execute(drafts_q)).scalars().all())
    total = sum(d.quantity_kg for d in drafts)

    if received_kg > 0 and total != received_kg:
        raise HTTPException(
            status_code=400,
            detail=f"Soma ({total} kg) != recebido ({received_kg} kg). Diferenca: {received_kg - total} kg",
        )

    for d in drafts:
        d.status = "CONFIRMADA"

    slid = await _seller_level_id(db)
    created_goals = 0
    for d in drafts:
        dest = await db.execute(
            select(HierarchyNode).where(HierarchyNode.id == d.destination_node_id)
        )
        dest_node = dest.scalar_one_or_none()
        if dest_node and dest_node.level_id == slid and d.product_id:
            existing = await db.execute(
                select(SellerGoal).where(
                    SellerGoal.cycle_id == cycle_id,
                    SellerGoal.product_id == d.product_id,
                    SellerGoal.seller_node_id == d.destination_node_id,
                )
            )
            sg = existing.scalar_one_or_none()
            if sg:
                sg.quantity_kg = d.quantity_kg
            else:
                db.add(SellerGoal(
                    cycle_id=cycle_id,
                    category_id=category_id,
                    product_id=d.product_id,
                    seller_node_id=d.destination_node_id,
                    quantity_kg=d.quantity_kg,
                    created_by_id=current_user.id,
                ))
            created_goals += 1

    await db.commit()
    return {
        "confirmed": len(drafts),
        "total_kg": str(total),
        "seller_goals_created": created_goals,
    }


@router.delete("/distributions/{dist_id}", status_code=204)
async def delete_distribution(
    dist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = await db.execute(select(Distribution).where(Distribution.id == dist_id))
    dist = r.scalar_one_or_none()
    if not dist:
        raise HTTPException(status_code=404)
    if dist.status == "CONFIRMADA":
        raise HTTPException(status_code=400, detail="Nao pode excluir confirmada")
    await db.delete(dist)
    await db.commit()


# ── Suggestions ─────────────────────────────────────────

@router.post(
    "/workspace/{cycle_id}/{category_id}/{source_node_id}/suggest",
    response_model=SuggestionResult,
)
async def suggest(
    cycle_id: int, category_id: int, source_node_id: int,
    body: SuggestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from api.services.engines import get_engine
    engine = get_engine(body.engine)
    product_level = await _is_product_level(db, source_node_id)
    return await engine.suggest(
        db, source_node_id, cycle_id, category_id, product_level,
        start_month=body.start_month, end_month=body.end_month,
    )


# ── Client Targets ──────────────────────────────────────

@router.get("/seller-goals/{goal_id}/clients", response_model=list[ClientTargetRead])
async def list_client_targets(goal_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(GoalClientTarget).where(GoalClientTarget.seller_goal_id == goal_id)
        .order_by(GoalClientTarget.client_name)
    )
    return r.scalars().all()


@router.post("/seller-goals/{goal_id}/clients", response_model=ClientTargetRead, status_code=201)
async def add_client_target(
    goal_id: int, body: ClientTargetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = GoalClientTarget(
        seller_goal_id=goal_id, client_code=body.client_code,
        client_name=body.client_name, quantity_kg=body.quantity_kg,
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


# ── Substitutions ───────────────────────────────────────

@router.get("/substitutions", response_model=list[SubstitutionRead])
async def list_substitutions(
    cycle_id: int | None = None, db: AsyncSession = Depends(get_db),
):
    query = select(SellerSubstitution).order_by(SellerSubstitution.created_at.desc())
    if cycle_id:
        query = query.where(SellerSubstitution.cycle_id == cycle_id)
    out = []
    for s in (await db.execute(query)).scalars().all():
        tit = (await db.execute(select(HierarchyNode.name).where(HierarchyNode.id == s.titular_node_id))).scalar() or ""
        sub = (await db.execute(select(HierarchyNode.name).where(HierarchyNode.id == s.substitute_node_id))).scalar() or ""
        out.append(SubstitutionRead(
            id=s.id, titular_node_id=s.titular_node_id, titular_name=tit,
            substitute_node_id=s.substitute_node_id, substitute_name=sub,
            cycle_id=s.cycle_id, starts_on=str(s.starts_on), ends_on=str(s.ends_on), notes=s.notes,
        ))
    return out


@router.post("/substitutions", response_model=SubstitutionRead, status_code=201)
async def create_substitution(
    body: SubstitutionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = SellerSubstitution(
        titular_node_id=body.titular_node_id, substitute_node_id=body.substitute_node_id,
        cycle_id=body.cycle_id, starts_on=body.starts_on, ends_on=body.ends_on,
        notes=body.notes, created_by_id=current_user.id,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    tit = (await db.execute(select(HierarchyNode.name).where(HierarchyNode.id == sub.titular_node_id))).scalar() or ""
    sub_name = (await db.execute(select(HierarchyNode.name).where(HierarchyNode.id == sub.substitute_node_id))).scalar() or ""
    return SubstitutionRead(
        id=sub.id, titular_node_id=sub.titular_node_id, titular_name=tit,
        substitute_node_id=sub.substitute_node_id, substitute_name=sub_name,
        cycle_id=sub.cycle_id, starts_on=str(sub.starts_on), ends_on=str(sub.ends_on), notes=sub.notes,
    )


# ── Categories ─────────────────────────────────────────

from pydantic import BaseModel as _BaseModel


class CategoryRead(_BaseModel):
    id: int
    source_id: str
    name: str
    is_active: bool
    products_count: int = 0
    model_config = {"from_attributes": True}


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProductCategory).order_by(ProductCategory.name)
    )
    out = []
    for cat in result.scalars().all():
        count = (await db.execute(
            select(func.count(Product.id)).where(
                Product.category_id == cat.id, Product.is_active == True,  # noqa: E712
            )
        )).scalar() or 0
        r = CategoryRead.model_validate(cat)
        r.products_count = count
        out.append(r)
    return out


# ── Gerencia ───────────────────────────────────────────

class GerenciaCategoryBudget(_BaseModel):
    category_id: int
    category_name: str
    budget_kg: Decimal
    distributed_kg: Decimal
    remaining_kg: Decimal
    children_count: int
    is_confirmed: bool


class GerenciaOverview(_BaseModel):
    cycle_id: int
    cycle_label: str
    gerente_node_id: int
    gerente_name: str
    categories: list[GerenciaCategoryBudget]


class BudgetSetItem(_BaseModel):
    category_id: int
    budget_kg: Decimal


class BudgetSetRequest(_BaseModel):
    items: list[BudgetSetItem]


async def _resolve_gerente_node(
    db: AsyncSession, current_user: User, node_id: int | None = None,
) -> HierarchyNode:
    """Resolve o nó gerencial:
    - GERENTE: usa seu scope_node_id
    - ADMINISTRADOR: usa node_id se fornecido, senão busca o primeiro gerente
    - Outros: 403
    """
    if current_user.role == "GERENTE":
        if not current_user.scope_node_id:
            raise HTTPException(status_code=400, detail="Usuario gerente sem escopo definido")
        result = await db.execute(
            select(HierarchyNode).where(HierarchyNode.id == current_user.scope_node_id)
        )
        node = result.scalar_one_or_none()
        if not node:
            raise HTTPException(status_code=404, detail="No gerencial nao encontrado")
        return node

    if current_user.role == "ADMINISTRADOR":
        if node_id:
            result = await db.execute(
                select(HierarchyNode).where(HierarchyNode.id == node_id)
            )
            node = result.scalar_one_or_none()
            if not node:
                raise HTTPException(status_code=404, detail="No gerencial nao encontrado")
            return node
        gerente_level = (await db.execute(
            select(HierarchyLevel).where(HierarchyLevel.depth == 1)
        )).scalar_one_or_none()
        if not gerente_level:
            raise HTTPException(status_code=404, detail="Nivel Gerente nao configurado")
        result = await db.execute(
            select(HierarchyNode).where(
                HierarchyNode.level_id == gerente_level.id,
                HierarchyNode.is_active == True,  # noqa: E712
            )
        )
        node = result.scalar_one_or_none()
        if not node:
            raise HTTPException(status_code=404, detail="Nenhum gerente encontrado")
        return node

    raise HTTPException(status_code=403, detail="Apenas Gerente ou Administrador podem acessar")


@router.get("/gerencia/nodes", response_model=list[dict])
async def list_gerente_nodes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista nós gerenciais disponíveis (para admin escolher)."""
    if current_user.role == "GERENTE":
        if current_user.scope_node_id:
            node = (await db.execute(
                select(HierarchyNode).where(HierarchyNode.id == current_user.scope_node_id)
            )).scalar_one_or_none()
            return [{"id": node.id, "name": node.name}] if node else []
        return []

    if current_user.role != "ADMINISTRADOR":
        raise HTTPException(status_code=403)

    gerente_level = (await db.execute(
        select(HierarchyLevel).where(HierarchyLevel.depth == 1)
    )).scalar_one_or_none()
    if not gerente_level:
        return []
    result = await db.execute(
        select(HierarchyNode).where(
            HierarchyNode.level_id == gerente_level.id,
            HierarchyNode.is_active == True,  # noqa: E712
        ).order_by(HierarchyNode.name)
    )
    return [{"id": n.id, "name": n.name} for n in result.scalars().all()]


@router.get("/gerencia/{cycle_id}", response_model=GerenciaOverview)
async def gerencia_overview(
    cycle_id: int,
    node_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle = (await db.execute(
        select(GoalCycle).where(GoalCycle.id == cycle_id)
    )).scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")

    gerente_node = await _resolve_gerente_node(db, current_user, node_id)

    children_result = await db.execute(
        select(func.count(HierarchyNode.id)).where(
            HierarchyNode.parent_id == gerente_node.id,
            HierarchyNode.is_active == True,  # noqa: E712
        )
    )
    children_count = children_result.scalar() or 0

    categories_result = await db.execute(
        select(ProductCategory).where(ProductCategory.is_active == True).order_by(ProductCategory.name)  # noqa: E712
    )
    categories = []
    for cat in categories_result.scalars().all():
        budget_row = await db.execute(
            select(Distribution.quantity_kg, Distribution.status).where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == cat.id,
                Distribution.destination_node_id == gerente_node.id,
                Distribution.product_id == None,  # noqa: E711
            )
        )
        row = budget_row.first()
        budget_kg = Decimal(str(row[0])) if row else Decimal("0")
        is_confirmed = row[1] == "CONFIRMADA" if row else False

        dist_result = await db.execute(
            select(func.coalesce(func.sum(Distribution.quantity_kg), 0)).where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == cat.id,
                Distribution.source_node_id == gerente_node.id,
                Distribution.product_id == None,  # noqa: E711
            )
        )
        distributed_kg = dist_result.scalar() or Decimal("0")

        categories.append(GerenciaCategoryBudget(
            category_id=cat.id,
            category_name=cat.name,
            budget_kg=budget_kg,
            distributed_kg=distributed_kg,
            remaining_kg=budget_kg - distributed_kg,
            children_count=children_count,
            is_confirmed=is_confirmed,
        ))

    return GerenciaOverview(
        cycle_id=cycle_id,
        cycle_label=f"{cycle.month:02d}/{cycle.year}",
        gerente_node_id=gerente_node.id,
        gerente_name=gerente_node.name,
        categories=categories,
    )


@router.put("/gerencia/{cycle_id}/budget")
async def set_gerencia_budget(
    cycle_id: int,
    body: BudgetSetRequest,
    node_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle = (await db.execute(
        select(GoalCycle).where(GoalCycle.id == cycle_id)
    )).scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")

    gerente_node = await _resolve_gerente_node(db, current_user, node_id)

    updated = 0
    for item in body.items:
        if item.budget_kg <= 0:
            continue

        existing = await db.execute(
            select(Distribution).where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == item.category_id,
                Distribution.destination_node_id == gerente_node.id,
                Distribution.product_id == None,  # noqa: E711
            )
        )
        dist = existing.scalar_one_or_none()
        if dist:
            dist.quantity_kg = item.budget_kg
            dist.status = "CONFIRMADA"
        else:
            db.add(Distribution(
                cycle_id=cycle_id,
                category_id=item.category_id,
                product_id=None,
                source_node_id=None,
                destination_node_id=gerente_node.id,
                quantity_kg=item.budget_kg,
                status="CONFIRMADA",
                engine_used="manual",
                created_by_id=current_user.id,
            ))
        updated += 1

    await db.commit()
    return {"updated": updated}


# ── Node Dashboard (painel generico por nivel) ──────────────


class NodeCategoryStatus(_BaseModel):
    category_id: int
    category_name: str
    received_kg: Decimal
    distributed_kg: Decimal
    remaining_kg: Decimal
    is_fully_distributed: bool


class SubordinateStatus(_BaseModel):
    node_id: int
    node_name: str
    level_name: str
    total_received_kg: Decimal
    total_distributed_kg: Decimal
    has_distributed: bool


class NodeDashboard(_BaseModel):
    node_id: int
    node_name: str
    level_name: str
    cycle_id: int
    cycle_label: str
    categories: list[NodeCategoryStatus]
    subordinates: list[SubordinateStatus]


@router.get("/node-dashboard", response_model=NodeDashboard)
async def node_dashboard(
    cycle_id: int,
    node_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resolved_id = node_id or current_user.scope_node_id
    if not resolved_id:
        raise HTTPException(status_code=400, detail="Usuario sem escopo hierarquico")

    node = await _node_with_level(db, resolved_id)
    if not node:
        raise HTTPException(status_code=404, detail="No nao encontrado")

    cycle = (await db.execute(
        select(GoalCycle).where(GoalCycle.id == cycle_id)
    )).scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")

    cats_result = await db.execute(
        select(ProductCategory).where(
            ProductCategory.is_active == True  # noqa: E712
        ).order_by(ProductCategory.name)
    )

    categories = []
    for cat in cats_result.scalars().all():
        received = await db.execute(
            select(func.coalesce(func.sum(Distribution.quantity_kg), 0)).where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == cat.id,
                Distribution.destination_node_id == resolved_id,
                Distribution.status == "CONFIRMADA",
            )
        )
        received_kg = received.scalar() or Decimal("0")

        distributed = await db.execute(
            select(func.coalesce(func.sum(Distribution.quantity_kg), 0)).where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == cat.id,
                Distribution.source_node_id == resolved_id,
            )
        )
        distributed_kg = distributed.scalar() or Decimal("0")

        if received_kg > 0:
            categories.append(NodeCategoryStatus(
                category_id=cat.id,
                category_name=cat.name,
                received_kg=received_kg,
                distributed_kg=distributed_kg,
                remaining_kg=received_kg - distributed_kg,
                is_fully_distributed=received_kg == distributed_kg and distributed_kg > 0,
            ))

    children_result = await db.execute(
        select(HierarchyNode)
        .options(selectinload(HierarchyNode.level))
        .where(
            HierarchyNode.parent_id == resolved_id,
            HierarchyNode.is_active == True,  # noqa: E712
        ).order_by(HierarchyNode.name)
    )

    subordinates = []
    for child in children_result.scalars().all():
        child_received = await db.execute(
            select(func.coalesce(func.sum(Distribution.quantity_kg), 0)).where(
                Distribution.cycle_id == cycle_id,
                Distribution.destination_node_id == child.id,
                Distribution.status == "CONFIRMADA",
            )
        )
        child_received_kg = child_received.scalar() or Decimal("0")

        child_distributed = await db.execute(
            select(func.coalesce(func.sum(Distribution.quantity_kg), 0)).where(
                Distribution.cycle_id == cycle_id,
                Distribution.source_node_id == child.id,
            )
        )
        child_distributed_kg = child_distributed.scalar() or Decimal("0")

        subordinates.append(SubordinateStatus(
            node_id=child.id,
            node_name=child.name,
            level_name=child.level.name if child.level else "",
            total_received_kg=child_received_kg,
            total_distributed_kg=child_distributed_kg,
            has_distributed=child_distributed_kg > 0,
        ))

    return NodeDashboard(
        node_id=resolved_id,
        node_name=node.name,
        level_name=node.level.name if node.level else "",
        cycle_id=cycle_id,
        cycle_label=f"{cycle.month:02d}/{cycle.year}",
        categories=categories,
        subordinates=subordinates,
    )


# ── Gerencia Targets (meta diaria / individual / por subgrupo) ─


class ProductTarget(_BaseModel):
    product_id: int
    product_name: str
    sum_3m: Decimal
    daily_avg: Decimal
    individual_target: Decimal


class CategoryTargets(_BaseModel):
    category_id: int
    category_name: str
    products: list[ProductTarget]
    total_sum_3m: Decimal
    total_daily_avg: Decimal
    total_individual: Decimal
    current_meta: Decimal


class TargetsOverview(_BaseModel):
    cycle_id: int
    cycle_label: str
    gerente_node_id: int
    gerente_name: str
    target_working_days: int
    prev_working_days: int
    categories: list[CategoryTargets]


class HierarchyStatus(_BaseModel):
    node_id: int
    node_name: str
    level_name: str
    depth: int
    parent_name: str
    has_distributed: bool
    total_received: Decimal
    total_distributed: Decimal


class DashboardData(_BaseModel):
    targets: TargetsOverview
    hierarchy_status: list[HierarchyStatus]


@router.get("/gerencia/{cycle_id}/dashboard", response_model=DashboardData)
async def gerencia_dashboard(
    cycle_id: int,
    node_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from collections import defaultdict
    from sqlalchemy import and_, extract, or_
    from api.models.portfolio import BaseDistribution
    from api.services.erp.normalize import normalize_name
    from api.services.working_days import get_effective_working_days, previous_months

    cycle = (await db.execute(
        select(GoalCycle).where(GoalCycle.id == cycle_id)
    )).scalar_one_or_none()
    if not cycle:
        raise HTTPException(status_code=404, detail="Ciclo nao encontrado")

    gerente_node = await _resolve_gerente_node(db, current_user, node_id)

    # ── Dias uteis ──
    target_wd = await get_effective_working_days(db, cycle.year, cycle.month)
    prev_months_list = previous_months(cycle.year, cycle.month, 3)
    prev_wd = 0
    for py, pm in prev_months_list:
        prev_wd += await get_effective_working_days(db, py, pm)
    if prev_wd <= 0:
        prev_wd = 1

    # ── Base distribution dos 3 meses anteriores ──
    month_filters = [
        and_(
            extract("year", BaseDistribution.month) == py,
            extract("month", BaseDistribution.month) == pm,
        )
        for py, pm in prev_months_list
    ]

    base_rows = []
    if month_filters:
        result = await db.execute(
            select(BaseDistribution).where(
                BaseDistribution.cycle_id == cycle_id,
                or_(*month_filters),
            )
        )
        base_rows = list(result.scalars().all())

    # ── Produtos por categoria ──
    cats_result = await db.execute(
        select(ProductCategory).where(
            ProductCategory.is_active == True  # noqa: E712
        ).order_by(ProductCategory.name)
    )
    all_categories = list(cats_result.scalars().all())

    prods_result = await db.execute(
        select(Product).where(Product.is_active == True).order_by(Product.name)  # noqa: E712
    )
    all_products = list(prods_result.scalars().all())

    prod_by_norm: dict[str, Product] = {
        normalize_name(p.name): p for p in all_products
    }
    prods_by_cat: dict[int, list[Product]] = defaultdict(list)
    for p in all_products:
        prods_by_cat[p.category_id].append(p)

    # ── Agregar base_distribution por produto ──
    sales_by_prod: dict[int, Decimal] = defaultdict(Decimal)
    for row in base_rows:
        prod = prod_by_norm.get(normalize_name(row.product_name))
        if prod:
            sales_by_prod[prod.id] += row.total_kg

    # ── Montar categorias com targets ──
    categories = []
    for cat in all_categories:
        products_in_cat = prods_by_cat.get(cat.id, [])
        prod_targets = []
        cat_sum = Decimal("0")
        cat_daily = Decimal("0")
        cat_individual = Decimal("0")

        for p in products_in_cat:
            s3m = sales_by_prod.get(p.id, Decimal("0"))
            if s3m <= 0:
                continue
            daily = s3m / Decimal(str(prev_wd))
            individual = (daily * Decimal(str(target_wd))).quantize(Decimal("1"))
            prod_targets.append(ProductTarget(
                product_id=p.id,
                product_name=p.name,
                sum_3m=s3m,
                daily_avg=daily.quantize(Decimal("0.01")),
                individual_target=individual,
            ))
            cat_sum += s3m
            cat_daily += daily
            cat_individual += individual

        # Meta atual (distribution confirmada para o gerente)
        budget_row = await db.execute(
            select(Distribution.quantity_kg).where(
                Distribution.cycle_id == cycle_id,
                Distribution.category_id == cat.id,
                Distribution.destination_node_id == gerente_node.id,
                Distribution.product_id == None,  # noqa: E711
                Distribution.status == "CONFIRMADA",
            )
        )
        current_meta = budget_row.scalar() or Decimal("0")

        categories.append(CategoryTargets(
            category_id=cat.id,
            category_name=cat.name,
            products=prod_targets,
            total_sum_3m=cat_sum,
            total_daily_avg=cat_daily.quantize(Decimal("0.01")),
            total_individual=cat_individual,
            current_meta=current_meta,
        ))

    targets = TargetsOverview(
        cycle_id=cycle_id,
        cycle_label=f"{cycle.month:02d}/{cycle.year}",
        gerente_node_id=gerente_node.id,
        gerente_name=gerente_node.name,
        target_working_days=target_wd,
        prev_working_days=prev_wd,
        categories=categories,
    )

    # ── Status da hierarquia ──
    all_nodes_result = await db.execute(
        select(HierarchyNode)
        .options(selectinload(HierarchyNode.level))
        .where(HierarchyNode.is_active == True)  # noqa: E712
        .order_by(HierarchyNode.level_id, HierarchyNode.name)
    )
    all_nodes = list(all_nodes_result.scalars().all())
    nodes_by_id = {n.id: n for n in all_nodes}

    seller_level_id = await _seller_level_id(db)

    statuses = []
    for node in all_nodes:
        if not node.level or node.level_id == seller_level_id:
            continue

        received_result = await db.execute(
            select(func.coalesce(func.sum(Distribution.quantity_kg), 0)).where(
                Distribution.cycle_id == cycle_id,
                Distribution.destination_node_id == node.id,
                Distribution.status == "CONFIRMADA",
            )
        )
        total_received = received_result.scalar() or Decimal("0")

        distributed_result = await db.execute(
            select(func.coalesce(func.sum(Distribution.quantity_kg), 0)).where(
                Distribution.cycle_id == cycle_id,
                Distribution.source_node_id == node.id,
            )
        )
        total_distributed = distributed_result.scalar() or Decimal("0")

        parent_name = ""
        if node.parent_id and node.parent_id in nodes_by_id:
            parent_name = nodes_by_id[node.parent_id].name

        statuses.append(HierarchyStatus(
            node_id=node.id,
            node_name=node.name,
            level_name=node.level.name if node.level else "",
            depth=node.level.depth if node.level else 0,
            parent_name=parent_name,
            has_distributed=total_distributed > 0,
            total_received=total_received,
            total_distributed=total_distributed,
        ))

    return DashboardData(targets=targets, hierarchy_status=statuses)
