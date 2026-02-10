"""
Injeção de dependências: DB, auth, roles.
Usuários vêm da tabela ctrl.users (banco SAFS).
"""
from typing import Annotated, List

from fastapi import Depends, Header
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, ServiceUnavailableError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_auth_db_session_gen, get_db_session_gen
from app.repositories.user_repository import get_by_id, profile_id_to_role
from app.schemas.auth import Role, UserMe


def get_db_session():
    """Fornece sessão DB analytics (powerbi)."""
    yield from get_db_session_gen()


def get_auth_db_session():
    """Fornece sessão DB auth (safs – ctrl.users)."""
    yield from get_auth_db_session_gen()


DbSession = Annotated[Session, Depends(get_db_session)]
AuthDbSession = Annotated[Session, Depends(get_auth_db_session)]


def _get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    auth_session: AuthDbSession = None,
) -> UserMe:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid authorization header")
    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired token")
    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Invalid token payload")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise UnauthorizedError("Invalid token payload")
    try:
        user = get_by_id(auth_session, user_id)
    except OperationalError:
        raise ServiceUnavailableError(
            "Não foi possível conectar ao banco de autenticação (SAFS). "
            "Verifique AUTH_DB_HOST e conectividade no .env."
        )
    if not user:
        raise UnauthorizedError("User not found or inactive")
    return UserMe(
        id=str(user.id),
        username=user.email,
        role=profile_id_to_role(user.profile_id),
        full_name=user.name,
    )


def require_roles(allowed_roles: List[Role]):
    """Dependency factory: exige um dos roles permitidos."""

    def role_check(current_user: Annotated[UserMe, Depends(_get_current_user)]) -> UserMe:
        if current_user.role not in allowed_roles:
            raise ForbiddenError("Insufficient permissions for this resource")
        return current_user

    return role_check


CurrentUser = Annotated[UserMe, Depends(_get_current_user)]
RequireAdmin = Annotated[UserMe, Depends(require_roles(["admin"]))]
RequireAnalyst = Annotated[UserMe, Depends(require_roles(["admin", "analyst"]))]
RequireReadOnly = Annotated[UserMe, Depends(require_roles(["admin", "analyst", "read_only"]))]
