from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: str
    scope_node_id: int | None
    is_active: bool

    model_config = {"from_attributes": True}
