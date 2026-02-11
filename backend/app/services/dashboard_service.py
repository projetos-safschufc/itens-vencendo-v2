"""
Serviço orquestrado: dashboard de estoque a vencer (180 dias).
"""
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import get_stock_expiry
from app.schemas.dashboard import (
    ChartSeries,
    DashboardCharts,
    DashboardFilters,
    DashboardMetrics,
    StockExpiryRow,
    StockExpiryResponse,
)


def _to_date(val: Any) -> Optional[date]:
    """Normaliza valor para date (vindo do banco como date, datetime ou string)."""
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        return datetime.strptime(str(val).strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _row_to_dto(row: dict) -> StockExpiryRow:
    return StockExpiryRow(
        material_code=row.get("material_code"),
        material_name=row.get("material_name"),
        warehouse=row.get("warehouse"),
        sector=row.get("sector"),
        group=row.get("material_group"),
        quantity=float(row.get("quantity") or 0),
        unit_value=float(row.get("unit_value") or 0),
        total_value=float(row.get("total_value") or 0),
        expiry_date=row.get("expiry_date"),
        days_until_expiry=int(row["days_until_expiry"]) if row.get("days_until_expiry") is not None else None,
    )


def get_stock_expiry_response(
    session: Session,
    filters: DashboardFilters,
    page: int = 1,
    page_size: int = 50,
) -> StockExpiryResponse:
    rows, total_rows, metrics, charts = get_stock_expiry(
        session,
        sector=filters.sector,
        warehouse=filters.warehouse,
        material_group=filters.material_group,
        expiry_from=filters.expiry_from,
        expiry_to=filters.expiry_to,
        material_search=filters.material_search,
        page=page,
        page_size=page_size,
    )
    today = date.today()
    # Garante tabela e card só com validade >= TODAY (defensivo; repositório já filtra por date.today())
    filtered_rows = []
    for r in rows:
        exp = _to_date(r.get("expiry_date"))
        if exp is not None and exp >= today:
            filtered_rows.append(r)
    rows = filtered_rows

    nearest_raw = metrics.get("nearest_expiry_date")
    nearest = None
    if nearest_raw is not None:
        # Normaliza para date (o banco pode retornar date, datetime ou string)
        if isinstance(nearest_raw, date) and not isinstance(nearest_raw, datetime):
            nearest = nearest_raw
        elif isinstance(nearest_raw, datetime):
            nearest = nearest_raw.date()
        else:
            try:
                nearest = datetime.strptime(str(nearest_raw)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                nearest = None
    # Card "Próxima validade": resultado da query MIN(validade) com validade >= hoje; nunca exibir data < hoje
    if nearest is not None and nearest < today:
        nearest = None
    metrics_dto = DashboardMetrics(
        total_value=float(metrics.get("total_value") or 0),
        items_count=int(metrics.get("items_count") or 0),
        distinct_warehouses=int(metrics.get("distinct_warehouses") or 0),
        nearest_expiry_date=nearest,
    )
    charts_dto = DashboardCharts(
        value_by_warehouse=[ChartSeries(label=x.get("label") or "", value=float(x.get("value") or 0)) for x in charts.get("value_by_warehouse") or []],
        value_by_expiry_month=[ChartSeries(label=x.get("label") or "", value=float(x.get("value") or 0)) for x in charts.get("value_by_expiry_month") or []],
        top_material_groups=[ChartSeries(label=x.get("label") or "", value=float(x.get("value") or 0)) for x in charts.get("top_material_groups") or []],
    )
    data_dto = [_row_to_dto(r) for r in rows]
    return StockExpiryResponse(
        filters=filters,
        metrics=metrics_dto,
        charts=charts_dto,
        data=data_dto,
        total_rows=total_rows,
        page=page,
        page_size=page_size,
    )
