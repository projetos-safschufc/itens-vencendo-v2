"""
Rotas: aba TESTE – tabela Material x Média últimos 6 meses.
"""
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy.exc import OperationalError

from app.core.logging_config import get_logger
from app.dependencies import DbSession, RequireReadOnly
from app.schemas.teste import TesteResponse
from app.services.teste_service import get_teste_response, get_default_month_labels

router = APIRouter(prefix="/teste", tags=["Teste"])
logger = get_logger(__name__)


@router.get("", response_model=TesteResponse)
def list_teste(
    session: DbSession,
    current_user: RequireReadOnly,
    material: Optional[str] = Query(None, description="Filtro por código ou descrição do material"),
):
    """Lista material e média dos últimos 6 meses. Opcional: filtrar por código (material)."""
    try:
        return get_teste_response(session, material=material)
    except OperationalError as e:
        logger.warning("teste_list_analytics_db_error", error=str(e), material_filter=material)
        return TesteResponse(
            data=[],
            total_rows=0,
            month_labels=get_default_month_labels(),
        )
    except Exception as e:
        logger.exception("teste_list_unexpected_error", error=str(e), material_filter=material)
        return TesteResponse(
            data=[],
            total_rows=0,
            month_labels=get_default_month_labels(),
        )
