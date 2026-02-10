"""
DTOs para Dashboard (estoque a vencer 180 dias).
"""
from datetime import date
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class DashboardFilters(BaseModel):
    sector: Optional[str] = None  # UACE | ULOG
    warehouse: Optional[str] = None
    material_group: Optional[str] = None
    expiry_from: Optional[date] = None
    expiry_to: Optional[date] = None
    material_search: Optional[str] = None


class StockExpiryRow(BaseModel):
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    warehouse: Optional[str] = None
    sector: Optional[str] = None
    group: Optional[str] = None
    quantity: float = 0
    unit_value: float = 0
    total_value: float = 0
    expiry_date: Optional[date] = None
    days_until_expiry: Optional[int] = None


class DashboardMetrics(BaseModel):
    total_value: float = 0
    items_count: int = 0
    distinct_warehouses: int = 0
    nearest_expiry_date: Optional[date] = None


class ChartSeries(BaseModel):
    label: str
    value: float
    extra: Optional[dict[str, Any]] = None


class DashboardCharts(BaseModel):
    value_by_warehouse: List[ChartSeries] = Field(default_factory=list)
    value_by_expiry_month: List[ChartSeries] = Field(default_factory=list)
    top_material_groups: List[ChartSeries] = Field(default_factory=list)


class DashboardFilterOptions(BaseModel):
    """Opções para SELECT-BOX de Almoxarifado e Grupo material."""
    almoxarifados: List[str] = Field(default_factory=list)
    grupos_material: List[str] = Field(default_factory=list)


class StockExpiryResponse(BaseModel):
    filters: DashboardFilters
    metrics: DashboardMetrics
    charts: DashboardCharts
    data: List[StockExpiryRow]
    total_rows: int
    page: int = 1
    page_size: int = 50
