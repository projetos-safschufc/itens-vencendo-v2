"""
Configuração centralizada baseada em ambiente.

Estratégia recomendada (arquivos separados):
- .env: configurações gerais; deixe DB_PASSWORD e AUTH_DB_PASSWORD vazios ou omita.
- .env.password (ou caminho em DB_PASSWORD_FILE): apenas senhas, no .gitignore.
  Formato: uma linha "senha" (mesma para ambos) ou linhas DB_PASSWORD=... e AUTH_DB_PASSWORD=...
  Linhas começando com # são comentários. Sem aspas no valor: DB_PASSWORD=abi123!@#qwe
- Na conexão: a senha é passada como string (parâmetro), nunca na URI, evitando
  problemas com #, @ e outros caracteres especiais.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus, unquote

from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz do backend: .env e .env.password são sempre carregados daqui (independente do CWD).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"

# Carrega .env do diretório do backend para os.environ.
load_dotenv(_ENV_FILE)


def _normalize_password(raw: str) -> str:
    """Remove \\r, \\n, BOM, zero-width e qualquer caractere não imprimável da senha."""
    if not raw:
        return ""
    s = (
        raw.replace("\r", "")
        .replace("\n", "")
        .replace("\ufeff", "")
        .replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\xa0", " ")
    )
    s = s.strip()
    # Garante que só sobram caracteres imprimíveis (remove qualquer invisível/controle restante)
    return "".join(c for c in s if c.isprintable()).strip()


def _get_password_file_path() -> Path:
    """Caminho do arquivo de senhas: DB_PASSWORD_FILE no .env ou padrão .env.password."""
    path_from_env = os.environ.get("DB_PASSWORD_FILE", "").strip()
    if path_from_env:
        p = Path(path_from_env)
        if not p.is_absolute():
            p = _BACKEND_ROOT / path_from_env
        return p
    return _BACKEND_ROOT / ".env.password"


def _load_passwords_from_env_password() -> None:
    """
    Preenche DB_PASSWORD e AUTH_DB_PASSWORD a partir do arquivo de senhas quando
    estiverem vazios ou com o placeholder de shell no .env.
    Arquivo (por padrão .env.password) pode ser:
    - Uma única linha: senha usada para ambos os bancos.
    - Linhas key=value: DB_PASSWORD=... e/ou AUTH_DB_PASSWORD=...
    Linhas que começam com # são ignoradas (comentário).
    """
    password_file = _get_password_file_path()
    if not password_file.is_file():
        return
    # utf-8-sig remove BOM se o arquivo foi salvo com marca BOM (ex.: Windows)
    raw = password_file.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return
    lines = [
        ln.strip().lstrip("\ufeff")
        for ln in raw.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    db_pass = os.environ.get("DB_PASSWORD", "").strip()
    auth_pass = os.environ.get("AUTH_DB_PASSWORD", "").strip()
    # Considera vazio ou placeholder de shell $(cat ...)
    need_db = not db_pass or db_pass.startswith("$(")
    need_auth = not auth_pass or auth_pass.startswith("$(")
    if not need_db and not need_auth:
        return
    single_password = None
    for line in lines:
        line = line.lstrip("\ufeff")  # BOM no meio do arquivo
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip().strip('"').strip("'")
            value = _normalize_password(value.strip().strip('"').strip("'"))
            if key == "DB_PASSWORD" and need_db:
                os.environ["DB_PASSWORD"] = value
                need_db = False
            elif key == "AUTH_DB_PASSWORD" and need_auth:
                os.environ["AUTH_DB_PASSWORD"] = value
                need_auth = False
        else:
            single_password = _normalize_password(line.strip('"').strip("'").lstrip("\ufeff"))
    if single_password is not None:
        if need_db:
            os.environ["DB_PASSWORD"] = single_password
        if need_auth:
            os.environ["AUTH_DB_PASSWORD"] = single_password


_load_passwords_from_env_password()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def strip_string_values(cls, data: dict) -> dict:
        """Remove espaços e normaliza senhas (evita caractere extra que causa auth failed)."""
        if not isinstance(data, dict):
            return data
        out = {}
        for k, v in data.items():
            if isinstance(v, str):
                v = v.strip()
                if "password" in (k or "").lower():
                    v = _normalize_password(v)
            out[k] = v
        return out

    # App
    app_name: str = "Inventory Analytics API"
    debug: bool = False
    environment: str = "development"

    # Database (analytics – powerbi)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "powerbi"
    db_user: str = ""
    db_password: str = ""
    db_schema: str = "gad_dlih_safs"

    # Database auth (safs – ctrl.users)
    auth_db_host: str = "localhost"
    auth_db_port: int = 5433
    auth_db_name: str = "safs"
    auth_db_user: str = ""
    auth_db_password: str = ""
    auth_db_schema: str = "ctrl"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Bcrypt (login): 8 = ~50–100 ms por verificação; 10 = ~200–400 ms. 8 é seguro e melhora UX.
    bcrypt_rounds: int = 8

    # Cache
    cache_ttl_seconds: int = 60

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Data de negócio: fuso para "hoje" (evita disparidade com data do Windows/usuário)
    business_timezone: str = "America/Sao_Paulo"
    # Opcional: forçar data de negócio (YYYY-MM-DD). Se definido, business_today() retorna esta data.
    business_date_override: Optional[str] = None

    def _encoded_user(self) -> str:
        """Usuário codificado para URL (ex.: @ em e-mail)."""
        return quote_plus(self.db_user, safe="")

    def _auth_encoded_user(self) -> str:
        return quote_plus(self.auth_db_user, safe="")

    def _decode_password(self, raw: str) -> str:
        """Decodifica senha: %23 → # etc. Use no .env a forma abi123!@%23qwe para evitar # como comentário."""
        if not raw:
            return raw
        return unquote(str(raw), encoding="utf-8", errors="replace")

    @property
    def db_password_decoded(self) -> str:
        """Senha do banco analytics (powerbi) pronta para connect_args. Decodifica %23 → #."""
        return self._decode_password(self.db_password)

    @property
    def auth_db_password_decoded(self) -> str:
        """Senha do banco SAFS pronta para connect_args. Decodifica %23 → #."""
        return self._decode_password(self.auth_db_password)

    @property
    def db_password_connection(self) -> str:
        """Valor de DB_PASSWORD normalizado para a conexão (sem \\r/\\n ou espaços extras)."""
        raw = (self.db_password or "").strip() if self.db_password is not None else ""
        return _normalize_password(raw)

    @property
    def auth_db_password_connection(self) -> str:
        """Valor de AUTH_DB_PASSWORD normalizado para a conexão (sem \\r/\\n ou espaços extras)."""
        raw = (self.auth_db_password or "").strip() if self.auth_db_password is not None else ""
        return _normalize_password(raw)

    def _encoded_password_for_url(self, password: str) -> str:
        """Codifica senha para uso na URL (# → %23, @ → %40, etc.). Evita que # seja interpretado como fragmento ou comentário no DSN."""
        if not password:
            return ""
        return quote_plus(password, safe="")

    @property
    def database_url(self) -> str:
        """URL SQLAlchemy (postgresql+psycopg2) com senha codificada."""
        pwd = self._encoded_password_for_url(self.db_password_decoded)
        return f"postgresql+psycopg2://{self._encoded_user()}:{pwd}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_uri_libpq(self) -> str:
        """URI no formato libpq (postgresql://) com senha CODIFICADA. Usada no creator para que o psycopg2 não monte DSN com password=... em texto (onde # vira comentário)."""
        pwd = self._encoded_password_for_url(self.db_password_decoded)
        return f"postgresql://{self._encoded_user()}:{pwd}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def auth_database_url(self) -> str:
        """URL do SAFS com senha codificada."""
        pwd = self._encoded_password_for_url(self.auth_db_password_decoded)
        return (
            f"postgresql+psycopg2://{self._auth_encoded_user()}:{pwd}"
            f"@{self.auth_db_host}:{self.auth_db_port}/{self.auth_db_name}"
        )

    @property
    def auth_database_uri_libpq(self) -> str:
        """URI libpq do SAFS com senha codificada e connect_timeout."""
        pwd = self._encoded_password_for_url(self.auth_db_password_decoded)
        base = f"postgresql://{self._auth_encoded_user()}:{pwd}@{self.auth_db_host}:{self.auth_db_port}/{self.auth_db_name}"
        return f"{base}?connect_timeout=5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
