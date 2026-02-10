"""
Repositório: ctrl.users (banco SAFS).
"""
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session, load_only

from app.constants import DEFAULT_ROLE, PROFILE_ID_TO_ROLE
from app.models.user import User


def get_by_email(session: Session, email: str) -> Optional[User]:
    """Busca usuário por e-mail (ativo). Carrega só colunas necessárias para login."""
    stmt = (
        select(User)
        .where(User.email == email.strip().lower(), User.status == "ativo")
        .options(load_only(User.id, User.email, User.password_hash, User.profile_id))
    )
    return session.execute(stmt).scalar_one_or_none()


def get_by_id(session: Session, user_id: int) -> Optional[User]:
    """Busca usuário por id (ativo)."""
    stmt = select(User).where(User.id == user_id, User.status == "ativo")
    return session.execute(stmt).scalar_one_or_none()


def profile_id_to_role(profile_id: int) -> str:
    """Converte profile_id para role da API."""
    return PROFILE_ID_TO_ROLE.get(profile_id, DEFAULT_ROLE)


def update_password_hash(session: Session, user_id: int, password_hash: str) -> None:
    """Atualiza o hash de senha do usuário (ex.: re-hash com menos rounds no login)."""
    session.execute(
        update(User).where(User.id == user_id).values(password_hash=password_hash)
    )
    session.commit()


def create_user(
    session: Session,
    *,
    name: str,
    email: str,
    password_hash: str,
    profile_id: int,
    status: str = "ativo",
) -> User:
    """Cria novo usuário em ctrl.users."""
    user = User(
        name=name.strip(),
        email=email.strip().lower(),
        password_hash=password_hash,
        profile_id=profile_id,
        status=status,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
