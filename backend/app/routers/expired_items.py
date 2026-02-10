"""
Rotas: histórico de itens vencidos.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.dependencies import DbSession, RequireReadOnly
from app.schemas.expired import ExpiredFilters, ExpiredFilterOptions, ExpiredItemsResponse
from app.services.expired_service import get_expired_items_response
from app.utils.export import (
    export_csv,
    export_expired_excel,
    export_expired_pdf,
    _format_validity_mm_yyyy,
)
from app.repositories.expired_repository import get_expired_filter_options

router = APIRouter(prefix="/expired-items", tags=["Expired Items"])


def _parse_date(value: Optional[str]):
    if not value or not str(value).strip():
        return None
    try:
        return datetime.fromisoformat(str(value).strip()).date()
    except (ValueError, TypeError):
        return None


@router.get("", response_model=ExpiredItemsResponse)
def list_expired_items(
    session: DbSession,
    current_user: RequireReadOnly,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    year: Optional[int] = Query(None, ge=2023, description="Filtro por ano (desde 2023)"),
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    filters = ExpiredFilters(
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        year=year,
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material=material,
    )
    return get_expired_items_response(session, filters, page=page, page_size=page_size)


@router.get("/metrics")
def get_metrics(
    session: DbSession,
    current_user: RequireReadOnly,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    year: Optional[int] = Query(None, ge=2023),
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
):
    filters = ExpiredFilters(
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        year=year,
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material=material,
    )
    resp = get_expired_items_response(session, filters, page=1, page_size=1)
    return resp.metrics


@router.get("/charts")
def get_charts(
    session: DbSession,
    current_user: RequireReadOnly,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    year: Optional[int] = Query(None, ge=2023),
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
):
    filters = ExpiredFilters(
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        year=year,
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material=material,
    )
    resp = get_expired_items_response(session, filters, page=1, page_size=1)
    return resp.charts


@router.get("/filter-options", response_model=ExpiredFilterOptions)
def list_filter_options(
    session: DbSession,
    current_user: RequireReadOnly,
    sector: Optional[str] = Query(None),
):
    """Almoxarifados e grupos de material para os filtros da tela (respeitando setor)."""
    opts = get_expired_filter_options(session, sector=sector)
    return ExpiredFilterOptions(**opts)


def _expired_export_rows(resp: ExpiredItemsResponse):
    """Converte dados da resposta para formato das exportações PDF/Excel (números brutos para Excel)."""
    return [
        {
            "material_name": r.material_name or r.material_code or "",
            "validity": _format_validity_mm_yyyy(r.validity),
            "quantity": float(r.quantity) if r.quantity is not None else 0,
            "unit_value": float(r.unit_value) if r.unit_value is not None else 0,
            "total_value": float(r.total_value) if r.total_value is not None else 0,
            "group": r.group or "",
            "warehouse": r.warehouse or "",
            "status": r.status or "VENCIDO",
        }
        for r in resp.data
    ]


def _expired_subtitle(date_from, date_to, year, sector, warehouse, material_group, material):
    parts = []
    if date_from:
        parts.append(f"Validade de: {date_from}")
    if date_to:
        parts.append(f"Validade até: {date_to}")
    if year is not None:
        parts.append(f"Ano: {year}")
    if sector:
        parts.append(f"Setor: {sector}")
    if warehouse:
        parts.append(f"Almoxarifado: {warehouse}")
    if material_group:
        parts.append(f"Grupo: {material_group}")
    if material:
        parts.append(f"Material: {material}")
    return " | ".join(parts) if parts else None


@router.post("/export/pdf")
def export_expired_pdf_route(
    session: DbSession,
    current_user: RequireReadOnly,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    year: Optional[int] = Query(None, ge=2023),
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
):
    filters = ExpiredFilters(
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        year=year,
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material=material,
    )
    resp = get_expired_items_response(session, filters, page=1, page_size=10000)
    rows = _expired_export_rows(resp)
    subtitle = _expired_subtitle(
        filters.date_from, filters.date_to, filters.year, sector, warehouse, material_group, material
    )
    return export_expired_pdf(
        title="Detalhes dos Itens Vencidos",
        rows=rows,
        filename="itens-vencidos.pdf",
        subtitle=subtitle,
    )


@router.post("/export/excel")
def export_expired_excel_route(
    session: DbSession,
    current_user: RequireReadOnly,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    year: Optional[int] = Query(None, ge=2023),
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
):
    filters = ExpiredFilters(
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        year=year,
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material=material,
    )
    resp = get_expired_items_response(session, filters, page=1, page_size=10000)
    rows = _expired_export_rows(resp)
    subtitle = _expired_subtitle(
        filters.date_from, filters.date_to, filters.year, sector, warehouse, material_group, material
    )
    return export_expired_excel(
        title="Detalhes dos Itens Vencidos",
        rows=rows,
        filename="itens-vencidos.xlsx",
        subtitle=subtitle,
    )


@router.post("/export/csv")
def export_expired_csv(
    session: DbSession,
    current_user: RequireReadOnly,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    year: Optional[int] = Query(None, ge=2023),
    sector: Optional[str] = Query(None),
    warehouse: Optional[str] = Query(None),
    material_group: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
):
    filters = ExpiredFilters(
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        year=year,
        sector=sector,
        warehouse=warehouse,
        material_group=material_group,
        material=material,
    )
    resp = get_expired_items_response(session, filters, page=1, page_size=10000)
    rows = [
        {
            "material_code": r.material_code,
            "material_name": r.material_name,
            "validity": _format_validity_mm_yyyy(r.validity),
            "quantity": r.quantity,
            "unit_value": r.unit_value,
            "total_value": r.total_value,
            "group": r.group,
            "warehouse": r.warehouse,
            "status": r.status or "VENCIDO",
        }
        for r in resp.data
    ]
    return export_csv(rows, "expired-items.csv")
