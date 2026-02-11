"""
Sessão de banco de dados e engine SQLAlchemy.
Conexão com parâmetros explícitos (host, user, password, etc.) para evitar que
caracteres especiais na senha (#, @, etc.) quebrem em URI ou DSN.
"""
from contextlib import contextmanager
from typing import Generator

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base

settings = get_settings()


def _creator_analytics():
    """Cria conexão ao banco de analytics (dw) com parâmetros explícitos; senha usada como string (DB_PASSWORD)."""
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password_connection,
        connect_timeout=5,
    )


def _creator_auth():
    """Cria conexão ao SAFS com parâmetros explícitos; senha usada como string (AUTH_DB_PASSWORD)."""
    return psycopg2.connect(
        host=settings.auth_db_host,
        port=settings.auth_db_port,
        dbname=settings.auth_db_name,
        user=settings.auth_db_user,
        password=settings.auth_db_password_connection,
        connect_timeout=5,
    )


# Engine usando creator: psycopg2.connect(uri) evita que a senha decodificada entre em DSN key=value onde # quebraria.
engine = create_engine(
    "postgresql+psycopg2://",
    creator=_creator_analytics,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.debug,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

auth_engine = create_engine(
    "postgresql+psycopg2://",
    creator=_creator_auth,
    pool_pre_ping=False,
    pool_size=5,
    max_overflow=5,
    pool_recycle=300,
    echo=settings.debug,
)
AuthSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)


def warm_up_auth_pool() -> None:
    """Aquece o pool do banco de autenticação (SAFS) no startup para o primeiro login não esperar conexão."""
    try:
        with auth_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pass  # não falha o startup; primeiro login ainda tenta conectar


def check_auth_connection() -> tuple[bool, str]:
    """
    Tenta uma conexão ao banco de autenticação (SAFS). Retorna (sucesso, mensagem).
    Usado no startup para diagnóstico no log (sem expor senha).
    """
    try:
        with auth_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as e:
        return False, str(e)


def check_analytics_connection() -> tuple[bool, str]:
    """
    Tenta uma conexão ao banco de analytics (dw). Retorna (sucesso, mensagem).
    Útil para diagnóstico no startup sem expor a senha.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as e:
        return False, str(e)


def init_db() -> None:
    """Cria tabelas se não existirem (para modelos locais). Views/tabelas do schema gad_dlih_safs já existem."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager para sessão de banco. Use em serviços/repositórios fora de request."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session_gen() -> Generator[Session, None, None]:
    """Generator para Depends(): uma sessão por request; commit/rollback sob controle do uso."""
    session = SessionLocal()
    try:
        # Alinha CURRENT_DATE do PostgreSQL ao fuso de negócio (ex.: America/Sao_Paulo)
        # Literal obrigatório: SET time zone não aceita parâmetro bound em alguns drivers
        tz = str(settings.business_timezone).replace("'", "''")
        session.execute(text(f"SET time zone '{tz}'"))
        yield session
    finally:
        session.close()


def get_auth_db_session_gen() -> Generator[Session, None, None]:
    """Sessão do banco SAFS (ctrl.users) para auth."""
    session = AuthSessionLocal()
    try:
        yield session
    finally:
        session.close()
