import uuid
from pydantic import BaseModel
from app.models.user import UserRole

class LoginRequest(BaseModel):
    phone: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    role: UserRole
    factory_id: uuid.UUID | None

    model_config = {"from_attributes": True}
