"""
API FastAPI: analytics de inventário hospitalar.
Documentação OpenAPI: /docs
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logging_config import configure_logging, get_logger
from app.db.session import check_analytics_connection, check_auth_connection, warm_up_auth_pool
from app.routers import auth, dashboard, expired_items, predictive, teste

settings = get_settings()
configure_logging(settings.environment)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app_name=settings.app_name)
    # Diagnóstico: comprimento da senha usada na conexão (string DB_PASSWORD)
    pwd_len = len(settings.db_password_connection or "")
    logger.info("analytics_db_config", host=settings.db_host, db=settings.db_name, user=settings.db_user, db_password_len=pwd_len)
    # Teste de conexão ao banco de analytics (powerbi) para diagnóstico no log
    loop = asyncio.get_running_loop()
    ok, msg = await loop.run_in_executor(None, check_analytics_connection)
    if ok:
        logger.info("analytics_db_connection_ok", host=settings.db_host, db=settings.db_name)
    else:
        logger.warning(
            "analytics_db_connection_failed",
            host=settings.db_host,
            db=settings.db_name,
            error=msg,
        )
    # Teste de conexão ao banco de autenticação (SAFS) para diagnóstico no log
    auth_ok, auth_msg = await loop.run_in_executor(None, check_auth_connection)
    if auth_ok:
        logger.info("auth_db_connection_ok", host=settings.auth_db_host, port=settings.auth_db_port, db=settings.auth_db_name)
    else:
        logger.warning(
            "auth_db_connection_failed",
            host=settings.auth_db_host,
            port=settings.auth_db_port,
            db=settings.auth_db_name,
            user=settings.auth_db_user,
            error=auth_msg,
        )
    # Aquece o pool do banco SAFS (ctrl.users) para o primeiro login não esperar conexão
    await loop.run_in_executor(None, warm_up_auth_pool)
    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    description="API REST para dashboard de analytics de inventário hospitalar (estoque a vencer, itens vencidos, análise preditiva).",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    """Garante que erros não tratados retornem JSON com detail (evita tela de login sem mensagem)."""
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno ao processar o login. Tente novamente ou verifique a conexão com o banco de autenticação (SAFS)."},
    )


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(expired_items.router)
app.include_router(predictive.router)
app.include_router(teste.router)
