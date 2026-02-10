"""
Rotas: análise preditiva (estoque por lote + risco e perda estimada).
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.dependencies import DbSession, RequireReadOnly
from app.schemas.predictive import PredictiveFilters, PredictiveResponse
from app.services.predictive_service import get_predictive_response
from app.utils.export import export_csv, export_excel, export_predictive_pdf


def _parse_as_of_date(value: Optional[str]) -> Optional[date]:
    """Converte as_of_date (YYYY-MM-DD) em date; retorna None se inválido ou vazio."""
    if not value or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except (ValueError, TypeError):
        return None

router = APIRouter(prefix="/predictive", tags=["Predictive"])


def _row_to_export(r) -> dict:
    return {
        "material_name": r.material_name or r.material_code or "",
        "material_group": r.material_group or "",
        "almoxarifado": r.warehouse or "",
        "lote": r.lote or "",
        "validity": str(r.validity) if r.validity else "",
        "days_until_expiry": r.days_until_expiry,
        "quantity": r.quantity,
        "unit_value": r.unit_value,
        "total_value": r.total_value,
        "avg_monthly_consumption": r.avg_monthly_consumption,
        "last_consumption_mesano": r.last_consumption_mesano or "",
        "qtde_ultimo_consumo": r.qtde_ultimo_consumo,
        "risk": r.risk,
        "predicted_loss_quantity": r.predicted_loss_quantity,
        "estimated_loss": r.estimated_loss,
    }


@router.post("/query", response_model=PredictiveResponse)
def predictive_query(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material_search: Optional[str] = Query(None),
    risk: Optional[str] = Query(None, description="Risco de Perda: ALTO RISCO, MÉDIO RISCO, BAIXO RISCO, SEM CONSUMO"),
    as_of_date: Optional[str] = Query(None, description="Data de referência YYYY-MM-DD (ex.: data do cabeçalho). Se omitida, usa a data do servidor."),
):
    filters = PredictiveFilters(
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material_search=material_search,
        risk=risk,
    )
    return get_predictive_response(session, filters, as_of_date=_parse_as_of_date(as_of_date))


@router.post("/export/excel")
def export_predictive_excel(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material_search: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    as_of_date: Optional[str] = Query(None),
):
    filters = PredictiveFilters(
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material_search=material_search,
        risk=risk,
    )
    resp = get_predictive_response(session, filters, as_of_date=_parse_as_of_date(as_of_date))
    rows = [_row_to_export(r) for r in resp.data]
    return export_excel(rows, "analise-preditiva.xlsx")


@router.post("/export/csv")
def export_predictive_csv(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material_search: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    as_of_date: Optional[str] = Query(None),
):
    filters = PredictiveFilters(
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material_search=material_search,
        risk=risk,
    )
    resp = get_predictive_response(session, filters, as_of_date=_parse_as_of_date(as_of_date))
    rows = [_row_to_export(r) for r in resp.data]
    return export_csv(rows, "analise-preditiva.csv")


def _export_subtitle(filters: PredictiveFilters) -> str:
    """Texto opcional com filtros aplicados para subtítulo do PDF."""
    parts = []
    if filters.sector:
        parts.append(f"Setor: {filters.sector}")
    if filters.warehouse:
        parts.append(f"Almoxarifado: {filters.warehouse}")
    if filters.material_group:
        parts.append(f"Grupo: {filters.material_group}")
    if filters.material_search:
        parts.append(f"Material: {filters.material_search}")
    if filters.risk:
        parts.append(f"Risco: {filters.risk}")
    return " | ".join(parts) if parts else ""


@router.post("/export/pdf")
def export_predictive_pdf_route(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material_search: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    as_of_date: Optional[str] = Query(None),
):
    filters = PredictiveFilters(
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material_search=material_search,
        risk=risk,
    )
    resp = get_predictive_response(session, filters, as_of_date=_parse_as_of_date(as_of_date))
    rows = [_row_to_export(r) for r in resp.data]
    subtitle = _export_subtitle(filters)
    return export_predictive_pdf(
        title="Análise preditiva – estoque por lote + risco e perda estimada",
        rows=rows,
        filename="analise-preditiva.pdf",
        subtitle=subtitle or None,
    )
