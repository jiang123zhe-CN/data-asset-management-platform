from datetime import datetime
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    display_name: str
    email: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    role: str = Field(default="data_entry")
    display_name: str = Field(min_length=1, max_length=50)
    email: str | None = None


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
    email: str | None = None
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=100)
