"""
DTOs de autenticação.
"""
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["admin", "analyst", "read_only"]


class LoginRequest(BaseModel):
    """Campo username = e-mail do usuário (ctrl.users.email)."""
    username: str  # e-mail
    password: str


class RegisterRequest(BaseModel):
    """Cadastro de novo usuário (apenas admin)."""
    name: str
    email: str
    password: str
    profile_id: int = 3  # 1=admin, 2=analyst, 3=read_only


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


class RefreshRequest(BaseModel):
    refresh_token: str


class UserMe(BaseModel):
    id: str
    username: str
    role: Role
    full_name: str | None = None
