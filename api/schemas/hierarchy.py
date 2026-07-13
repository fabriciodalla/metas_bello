from pydantic import BaseModel


class HierarchyLevelRead(BaseModel):
    id: int
    name: str
    depth: int
    prefix: str
    is_active: bool

    model_config = {"from_attributes": True}


class HierarchyNodeRead(BaseModel):
    id: int
    level_id: int
    parent_id: int | None
    source_id: str
    name: str
    is_active: bool
    level: HierarchyLevelRead | None = None

    model_config = {"from_attributes": True}


class HierarchyNodeCreate(BaseModel):
    level_id: int
    parent_id: int | None = None
    source_id: str
    name: str


class HierarchyNodeUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    is_active: bool | None = None


class HierarchyTreeNode(BaseModel):
    id: int
    source_id: str
    name: str
    level: HierarchyLevelRead
    is_active: bool
    children: list["HierarchyTreeNode"] = []

    model_config = {"from_attributes": True}


class HierarchyEventRead(BaseModel):
    id: int
    node_id: int
    node_name: str = ""
    event_type: str
    old_parent_id: int | None
    new_parent_id: int | None
    old_parent_name: str = ""
    new_parent_name: str = ""
    effective_on: str
    notes: str = ""
    created_at: str = ""

    model_config = {"from_attributes": True}


class HierarchyEventCreate(BaseModel):
    node_id: int
    event_type: str
    old_parent_id: int | None = None
    new_parent_id: int | None = None
    effective_on: str
    notes: str = ""
