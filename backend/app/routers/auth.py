"""
Rotas de autenticação: login (por e-mail), refresh, me, register (admin).
Usuários em ctrl.users (banco SAFS).
"""
import threading
import time
from fastapi import APIRouter, Depends
from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.core.exceptions import ServiceUnavailableError, UnauthorizedError, ValidationError
from app.core.logging_config import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_bcrypt_rounds_from_hash,
    get_password_hash,
    verify_password,
)
from app.db.session import AuthSessionLocal
from app.dependencies import AuthDbSession, CurrentUser
from app.repositories.user_repository import (
    create_user,
    get_by_email,
    get_by_id,
    profile_id_to_role,
    update_password_hash,
)
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserMe

logger = get_logger(__name__)


def _rehash_password_background(user_id: int, plain_password: str) -> None:
    """Atualiza hash para 8 rounds em thread separada; não bloqueia a resposta do login."""
    try:
        session = AuthSessionLocal()
        try:
            new_hash = get_password_hash(plain_password, rounds=8)
            update_password_hash(session, user_id, new_hash)
        finally:
            session.close()
    except Exception:
        pass

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _auth_db_unavailable() -> None:
    settings = get_settings()
    raise ServiceUnavailableError(
        "Não foi possível conectar ao banco de autenticação (SAFS). "
        f"Verifique no .env: AUTH_DB_HOST={getattr(settings, 'auth_db_host', '?')}, "
        f"AUTH_DB_PORT={getattr(settings, 'auth_db_port', '?')}, AUTH_DB_NAME={getattr(settings, 'auth_db_name', '?')}, "
        "AUTH_DB_USER e AUTH_DB_PASSWORD (ou .env.password). Confira rede/VPN e se o servidor SAFS está acessível."
    )


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, auth_session: AuthDbSession):
    """Autentica por e-mail e senha (ctrl.users)."""
    t0 = time.perf_counter()
    email = (credentials.username or "").strip().lower()
    password = (credentials.password or "").strip()
    if not email or "@" not in email:
        raise ValidationError("Informe um e-mail válido.")
    if not password:
        raise ValidationError("Informe a senha.")
    db_ms = 0
    try:
        t_db = time.perf_counter()
        user = get_by_email(auth_session, email)
        db_ms = round((time.perf_counter() - t_db) * 1000)
    except OperationalError:
        _auth_db_unavailable()
    if not user:
        logger.info("login_user_not_found", email=email, db_ms=db_ms)
        raise UnauthorizedError("E-mail ou senha inválidos")
    t_verify = time.perf_counter()
    ok = verify_password(password, user.password_hash)
    verify_ms = round((time.perf_counter() - t_verify) * 1000)
    if not ok:
        logger.info("login_invalid_password", email=email, db_ms=db_ms, verify_ms=verify_ms)
        raise UnauthorizedError("E-mail ou senha inválidos")
    # Re-hash em background: não atrasa a resposta; próximo login já usará hash com 8 rounds
    stored_rounds = get_bcrypt_rounds_from_hash(user.password_hash)
    if stored_rounds > 8:
        threading.Thread(
            target=_rehash_password_background,
            args=(user.id, password),
            daemon=True,
        ).start()
    total_ms = round((time.perf_counter() - t0) * 1000)
    logger.info(
        "login_ok",
        email=email,
        user_id=user.id,
        db_ms=db_ms,
        verify_ms=verify_ms,
        total_ms=total_ms,
        bcrypt_rounds=stored_rounds,
    )
    settings = get_settings()
    role = profile_id_to_role(user.profile_id)
    access = create_access_token(
        subject=str(user.id),
        extra_claims={"role": role, "user_id": user.id},
    )
    refresh = create_refresh_token(subject=str(user.id))
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, auth_session: AuthDbSession):
    """Gera novo access token a partir do refresh token."""
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedError("Refresh token inválido ou expirado")
    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Invalid refresh token")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise UnauthorizedError("Invalid refresh token")
    try:
        user = get_by_id(auth_session, user_id)
    except OperationalError:
        _auth_db_unavailable()
    if not user:
        raise UnauthorizedError("Usuário não encontrado ou inativo")
    settings = get_settings()
    role = profile_id_to_role(user.profile_id)
    access = create_access_token(
        subject=str(user.id),
        extra_claims={"role": role, "user_id": user.id},
    )
    new_refresh = create_refresh_token(subject=str(user.id))
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserMe)
def me(current_user: CurrentUser):
    """Retorna o usuário autenticado."""
    return current_user


@router.post("/register", response_model=UserMe)
def register(body: RegisterRequest, auth_session: AuthDbSession):
    """Cadastra novo usuário em ctrl.users. Formulário de cadastro pode ser exibido a qualquer usuário."""
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise ValidationError("E-mail inválido")
    try:
        existing = get_by_email(auth_session, email)
    except OperationalError:
        _auth_db_unavailable()
    if existing:
        raise ValidationError("E-mail já cadastrado")
    if not body.name or len(body.name.strip()) < 2:
        raise ValidationError("Nome deve ter ao menos 2 caracteres")
    if len(body.password) < 6:
        raise ValidationError("Senha deve ter ao menos 6 caracteres")
    password_hash = get_password_hash(body.password)
    try:
        user = create_user(
            auth_session,
            name=body.name,
            email=email,
            password_hash=password_hash,
            profile_id=body.profile_id,
        )
    except OperationalError:
        _auth_db_unavailable()
    return UserMe(
        id=str(user.id),
        username=user.email,
        role=profile_id_to_role(user.profile_id),
        full_name=user.name,
    )
