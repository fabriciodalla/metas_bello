from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database import get_db
from api.models.accounts import User
from api.models.hierarchy import HierarchyEvent, HierarchyLevel, HierarchyNode
from api.routers.auth import get_current_user
from api.schemas.hierarchy import (
    HierarchyEventCreate,
    HierarchyEventRead,
    HierarchyLevelRead,
    HierarchyNodeCreate,
    HierarchyNodeRead,
    HierarchyNodeUpdate,
    HierarchyTreeNode,
)

router = APIRouter(prefix="/hierarchy", tags=["hierarchy"])


@router.get("/levels", response_model=list[HierarchyLevelRead])
async def list_levels(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HierarchyLevel).order_by(HierarchyLevel.depth)
    )
    return result.scalars().all()


@router.get("/nodes", response_model=list[HierarchyNodeRead])
async def list_nodes(
    level_id: int | None = None,
    parent_id: int | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    query = select(HierarchyNode).options(selectinload(HierarchyNode.level))
    if level_id is not None:
        query = query.where(HierarchyNode.level_id == level_id)
    if parent_id is not None:
        query = query.where(HierarchyNode.parent_id == parent_id)
    if active_only:
        query = query.where(HierarchyNode.is_active == True)  # noqa: E712
    result = await db.execute(query.order_by(HierarchyNode.name))
    return result.scalars().all()


@router.get("/nodes/{node_id}", response_model=HierarchyNodeRead)
async def get_node(node_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HierarchyNode)
        .options(selectinload(HierarchyNode.level))
        .where(HierarchyNode.id == node_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node nao encontrado")
    return node


@router.get("/nodes/{node_id}/children", response_model=list[HierarchyNodeRead])
async def get_children(
    node_id: int,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(HierarchyNode)
        .options(selectinload(HierarchyNode.level))
        .where(HierarchyNode.parent_id == node_id)
    )
    if active_only:
        query = query.where(HierarchyNode.is_active == True)  # noqa: E712
    result = await db.execute(query.order_by(HierarchyNode.name))
    return result.scalars().all()


@router.get("/tree", response_model=list[HierarchyTreeNode])
async def get_tree(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HierarchyNode)
        .options(selectinload(HierarchyNode.level))
        .where(HierarchyNode.is_active == True)  # noqa: E712
        .order_by(HierarchyNode.level_id, HierarchyNode.name)
    )
    all_nodes = result.scalars().all()

    nodes_by_id = {}
    roots = []
    for node in all_nodes:
        tree_node = HierarchyTreeNode(
            id=node.id,
            source_id=node.source_id,
            name=node.name,
            level=HierarchyLevelRead.model_validate(node.level),
            is_active=node.is_active,
            children=[],
        )
        nodes_by_id[node.id] = tree_node

    for node in all_nodes:
        tree_node = nodes_by_id[node.id]
        if node.parent_id and node.parent_id in nodes_by_id:
            nodes_by_id[node.parent_id].children.append(tree_node)
        else:
            roots.append(tree_node)

    return roots


@router.post("/nodes", response_model=HierarchyNodeRead, status_code=201)
async def create_node(
    body: HierarchyNodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = HierarchyNode(**body.model_dump())
    db.add(node)

    event = HierarchyEvent(
        node_id=0,
        event_type="ENTRADA",
        new_parent_id=body.parent_id,
        effective_on=date.today(),
        created_by_id=current_user.id,
    )
    db.add(event)
    await db.flush()
    event.node_id = node.id
    await db.commit()
    await db.refresh(node, ["level"])
    return node


@router.patch("/nodes/{node_id}", response_model=HierarchyNodeRead)
async def update_node(
    node_id: int,
    body: HierarchyNodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(HierarchyNode)
        .options(selectinload(HierarchyNode.level))
        .where(HierarchyNode.id == node_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node nao encontrado")

    update_data = body.model_dump(exclude_unset=True)

    if "parent_id" in update_data and update_data["parent_id"] != node.parent_id:
        event = HierarchyEvent(
            node_id=node.id,
            event_type="TRANSFERENCIA",
            old_parent_id=node.parent_id,
            new_parent_id=update_data["parent_id"],
            effective_on=date.today(),
            created_by_id=current_user.id,
        )
        db.add(event)

    if "is_active" in update_data and update_data["is_active"] != node.is_active:
        event_type = "REATIVACAO" if update_data["is_active"] else "INATIVACAO"
        event = HierarchyEvent(
            node_id=node.id,
            event_type=event_type,
            old_parent_id=node.parent_id,
            new_parent_id=node.parent_id,
            effective_on=date.today(),
            created_by_id=current_user.id,
        )
        db.add(event)

    for key, value in update_data.items():
        setattr(node, key, value)
    await db.commit()
    await db.refresh(node, ["level"])
    return node


@router.get("/events", response_model=list[HierarchyEventRead])
async def list_events(
    node_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(HierarchyEvent).order_by(HierarchyEvent.created_at.desc())
    if node_id is not None:
        query = query.where(HierarchyEvent.node_id == node_id)
    result = await db.execute(query.limit(100))
    events = result.scalars().all()

    out = []
    for ev in events:
        node_result = await db.execute(
            select(HierarchyNode.name).where(HierarchyNode.id == ev.node_id)
        )
        node_name = node_result.scalar() or ""

        old_name, new_name = "", ""
        if ev.old_parent_id:
            r = await db.execute(
                select(HierarchyNode.name).where(HierarchyNode.id == ev.old_parent_id)
            )
            old_name = r.scalar() or ""
        if ev.new_parent_id:
            r = await db.execute(
                select(HierarchyNode.name).where(HierarchyNode.id == ev.new_parent_id)
            )
            new_name = r.scalar() or ""

        out.append(HierarchyEventRead(
            id=ev.id,
            node_id=ev.node_id,
            node_name=node_name,
            event_type=ev.event_type,
            old_parent_id=ev.old_parent_id,
            new_parent_id=ev.new_parent_id,
            old_parent_name=old_name,
            new_parent_name=new_name,
            effective_on=str(ev.effective_on),
            notes=ev.notes,
            created_at=str(ev.created_at),
        ))
    return out
