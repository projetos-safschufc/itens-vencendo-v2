"""
Serviço: histórico de itens vencidos e por ano.
Regra: período não informado = últimos 12 meses até a data atual.
"""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.expired_repository import get_expired_items
from app.schemas.expired import (
    ExpiredCharts,
    ExpiredFilters,
    ExpiredItemRow,
    ExpiredItemsResponse,
    ExpiredMetrics,
)


def _default_period() -> tuple[Optional[date], Optional[date]]:
    """Período padrão: últimos 12 meses até hoje."""
    today = date.today()
    date_to = today
    # date_from = today - timedelta(days=365)
    date_from = date(2023, 1, 1)
    return date_from, date_to


def get_expired_items_response(
    session: Session,
    filters: ExpiredFilters,
    page: int = 1,
    page_size: int = 50,
) -> ExpiredItemsResponse:
    date_from = filters.date_from
    date_to = filters.date_to
    # Filtro por ano define período 01/01 a 31/12; senão, sem datas = últimos 12 meses
    if filters.year is not None:
        date_from = None
        date_to = None
    elif date_from is None and date_to is None:
        date_from, date_to = _default_period()

    rows, total_rows, metrics, charts = get_expired_items(
        session,
        date_from=date_from,
        date_to=date_to,
        year=filters.year,
        sector=filters.sector,
        warehouse=filters.warehouse,
        material_group=filters.material_group,
        material=filters.material,
        page=page,
        page_size=page_size,
    )
    metrics_dto = ExpiredMetrics(
        total_lost_value=float(metrics.get("total_lost_value") or 0),
        total_expired_items=int(metrics.get("total_expired_items") or 0),
        average_loss_per_item=float(metrics.get("average_loss_per_item") or 0),
    )
    # Top 10 grupos: limitar no serviço se o repositório já não limitar
    by_group = charts.get("by_group") or []
    charts_dto = ExpiredCharts(
        monthly_series=charts.get("monthly_series") or [],
        by_group=by_group[:10],
        by_warehouse=charts.get("by_warehouse") or [],
        distinct_materials_per_month=charts.get("distinct_materials_per_month") or [],
        by_year=charts.get("by_year") or [],
    )
    data_dto = [
        ExpiredItemRow(
            material_code=r.get("material_code"),
            material_name=r.get("material_name"),
            validity=r.get("movement_date"),
            quantity=float(r.get("quantity") or 0),
            unit_value=float(r.get("unit_value") or 0),
            total_value=float(r.get("total_value") or 0),
            group=r.get("group_name"),
            warehouse=r.get("warehouse"),
            status="VENCIDO",
        )
        for r in rows
    ]
    return ExpiredItemsResponse(
        filters=filters,
        metrics=metrics_dto,
        charts=charts_dto,
        data=data_dto,
        total_rows=total_rows,
        page=page,
        page_size=page_size,
    )
