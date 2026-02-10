"""
Rotas do dashboard (estoque a vencer 180 dias).
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy.exc import OperationalError

from app.core.exceptions import ServiceUnavailableError
from app.core.logging_config import get_logger
from app.dependencies import DbSession, RequireReadOnly
from app.schemas.dashboard import DashboardFilterOptions, DashboardFilters, StockExpiryResponse
from app.repositories.dashboard_repository import get_filter_options
from app.services.dashboard_service import get_stock_expiry_response
from app.utils.export import export_dashboard_excel, export_pdf_simple

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
logger = get_logger(__name__)


def _handle_analytics_operational_error(e: OperationalError) -> None:
    logger.warning("analytics_db_connection_failed", error=str(e), exc_info=True)
    raise ServiceUnavailableError(
        "Não foi possível conectar ao banco de analytics (powerbi). "
        "Verifique DB_HOST, DB_PORT, rede/VPN e .env. Detalhe no log do servidor."
    )


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Converte string YYYY-MM-DD em date; retorna None se vazio ou inválido."""
    if not value or not str(value).strip():
        return None
    try:
        return datetime.fromisoformat(str(value).strip()).date()
    except (ValueError, TypeError):
        return None


@router.get("/filter-options", response_model=DashboardFilterOptions)
def get_filter_options_route(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
):
    """Listas de almoxarifados e grupos de material para os SELECT-BOX do dashboard."""
    try:
        options = get_filter_options(session, sector=sector)
        return DashboardFilterOptions(**options)
    except OperationalError as e:
        _handle_analytics_operational_error(e)


@router.get("/stock-expiry", response_model=StockExpiryResponse)
def get_stock_expiry(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    expiry_from: Optional[str] = Query(None),
    expiry_to: Optional[str] = Query(None),
    material_search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Dados completos do dashboard: métricas, gráficos e tabela paginada."""
    filters = DashboardFilters(
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        expiry_from=_parse_date(expiry_from),
        expiry_to=_parse_date(expiry_to),
        material_search=material_search,
    )
    try:
        return get_stock_expiry_response(session, filters, page=page, page_size=page_size)
    except OperationalError as e:
        _handle_analytics_operational_error(e)


@router.get("/metrics")
def get_metrics(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
):
    """Apenas métricas (KPIs)."""
    filters = DashboardFilters(sector=sector, warehouse=warehouse, material_group=material_group)
    try:
        resp = get_stock_expiry_response(session, filters, page=1, page_size=1)
        return resp.metrics
    except OperationalError as e:
        _handle_analytics_operational_error(e)


@router.get("/charts")
def get_charts(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
):
    """Apenas dados para gráficos."""
    filters = DashboardFilters(sector=sector, warehouse=warehouse, material_group=material_group)
    try:
        resp = get_stock_expiry_response(session, filters, page=1, page_size=1)
        return resp.charts
    except OperationalError as e:
        _handle_analytics_operational_error(e)


@router.post("/export/pdf")
def export_pdf(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    expiry_from: Optional[str] = Query(None),
    expiry_to: Optional[str] = Query(None),
    material_search: Optional[str] = Query(None),
):
    """Exportação PDF do estoque a vencer, respeitando os mesmos filtros do dashboard."""
    filters = DashboardFilters(
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        expiry_from=_parse_date(expiry_from),
        expiry_to=_parse_date(expiry_to),
        material_search=material_search,
    )
    try:
        resp = get_stock_expiry_response(session, filters, page=1, page_size=2000)
    except OperationalError as e:
        _handle_analytics_operational_error(e)
    # Construir linhas como dicts com valores já em string para o PDF
    rows = []
    for r in resp.data:
        raw = r.model_dump() if hasattr(r, "model_dump") else {"material_code": r.material_code, "material_name": r.material_name, "warehouse": r.warehouse, "quantity": r.quantity, "total_value": r.total_value, "expiry_date": r.expiry_date}
        val = float(raw.get("total_value") or 0)
        total_str = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        expiry = raw.get("expiry_date")
        expiry_str = str(expiry)[:10] if expiry else ""
        rows.append({
            "material_code": str(raw.get("material_code") or "").strip(),
            "material_name": str(raw.get("material_name") or "").strip(),
            "warehouse": str(raw.get("warehouse") or "").strip(),
            "quantity": str(int(float(raw.get("quantity") or 0))),
            "total_value": total_str,
            "expiry_date": expiry_str,
        })
    parts = []
    if sector:
        parts.append(f"Setor: {sector}")
    if warehouse:
        parts.append(f"Almoxarifado: {warehouse}")
    if material_group:
        parts.append(f"Grupo: {material_group}")
    if expiry_from:
        parts.append(f"Validade de: {expiry_from}")
    if expiry_to:
        parts.append(f"Validade até: {expiry_to}")
    if material_search and str(material_search).strip():
        parts.append(f"Busca: {material_search.strip()}")
    subtitle = " | ".join(parts) if parts else None
    return export_pdf_simple("Estoque a vencer (180 dias)", rows, "dashboard-stock-expiry.pdf", subtitle=subtitle)


@router.post("/export/excel")
def export_excel(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    expiry_from: Optional[str] = Query(None),
    expiry_to: Optional[str] = Query(None),
    material_search: Optional[str] = Query(None),
):
    """Exportação Excel do estoque a vencer, respeitando os mesmos filtros do dashboard."""
    filters = DashboardFilters(
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        expiry_from=_parse_date(expiry_from),
        expiry_to=_parse_date(expiry_to),
        material_search=material_search,
    )
    try:
        resp = get_stock_expiry_response(session, filters, page=1, page_size=2000)
    except OperationalError as e:
        _handle_analytics_operational_error(e)
    rows = []
    for r in resp.data:
        raw = r.model_dump() if hasattr(r, "model_dump") else {
            "material_code": r.material_code,
            "material_name": r.material_name,
            "warehouse": r.warehouse,
            "quantity": r.quantity,
            "total_value": r.total_value,
            "expiry_date": r.expiry_date,
        }
        val = float(raw.get("total_value") or 0)
        total_str = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        expiry = raw.get("expiry_date")
        expiry_str = str(expiry)[:10] if expiry else ""
        rows.append({
            "material_code": str(raw.get("material_code") or "").strip(),
            "material_name": str(raw.get("material_name") or "").strip(),
            "warehouse": str(raw.get("warehouse") or "").strip(),
            "quantity": str(int(float(raw.get("quantity") or 0))),
            "total_value": total_str,
            "expiry_date": expiry_str,
        })
    parts = []
    if sector:
        parts.append(f"Setor: {sector}")
    if warehouse:
        parts.append(f"Almoxarifado: {warehouse}")
    if material_group:
        parts.append(f"Grupo: {material_group}")
    if expiry_from:
        parts.append(f"Validade de: {expiry_from}")
    if expiry_to:
        parts.append(f"Validade até: {expiry_to}")
    if material_search and str(material_search).strip():
        parts.append(f"Busca: {material_search.strip()}")
    subtitle = " | ".join(parts) if parts else None
    return export_dashboard_excel(
        "Estoque a vencer (180 dias)",
        rows,
        "dashboard-stock-expiry.xlsx",
        subtitle=subtitle,
    )
