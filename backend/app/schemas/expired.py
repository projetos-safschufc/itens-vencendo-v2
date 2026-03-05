"""
DTOs para histórico de itens vencidos e por ano.
"""
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class ExpiredFilters(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    year: Optional[int] = None  # filtro por ano (desde 2023); define período 01/01 a 31/12
    sector: Optional[str] = None
    warehouse: Optional[str] = None
    material_group: Optional[str] = None
    material: Optional[str] = None


class ExpiredFilterOptions(BaseModel):
    warehouses: List[str] = Field(default_factory=list)
    material_groups: List[str] = Field(default_factory=list)


class ExpiredItemRow(BaseModel):
    """Linha da tabela Detalhes dos Itens Vencidos (mapeamento regra de negócio).
    A coluna Material exibe v_df_movimento.mat_cod_antigo (material_name)."""
    material_code: Optional[str] = None
    material_name: Optional[str] = None  # mat_cod_antigo da v_df_movimento / df_movimento
    validity: Optional[date] = None  # data de vencimento/registro (mesano)
    quantity: float = 0
    unit_value: float = 0
    total_value: float = 0
    group: Optional[str] = None
    warehouse: Optional[str] = None
    status: Optional[str] = "VENCIDO"


class ExpiredMetrics(BaseModel):
    total_lost_value: float = 0
    total_expired_items: int = 0
    average_loss_per_item: float = 0


class ExpiredCharts(BaseModel):
    monthly_series: List[dict] = Field(default_factory=list)
    by_group: List[dict] = Field(default_factory=list)
    by_warehouse: List[dict] = Field(default_factory=list)
    distinct_materials_per_month: List[dict] = Field(default_factory=list)
    by_year: List[dict] = Field(default_factory=list)  # perdas por ano (desde 2023)


class ExpiredItemsResponse(BaseModel):
    filters: ExpiredFilters
    metrics: ExpiredMetrics
    charts: ExpiredCharts
    data: List[ExpiredItemRow]
    total_rows: int
    page: int = 1
    page_size: int = 50
