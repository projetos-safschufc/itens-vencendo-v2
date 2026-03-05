"""
DTOs para análise preditiva (estoque por lote + consumo 6m, risco e perda estimada).
"""
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class PredictiveFilters(BaseModel):
    sector: Optional[str] = None
    warehouse: Optional[str] = None
    material_group: Optional[str] = None
    material_search: Optional[str] = None
    risk: Optional[str] = None  # ALTO RISCO | MÉDIO RISCO | BAIXO RISCO | SEM CONSUMO


# Risco: SEM_CONSUMO | ALTO_RISCO | MEDIO_RISCO | BAIXO_RISCO
RISCO_SEM_CONSUMO = "SEM CONSUMO"
RISCO_ALTO = "ALTO RISCO"
RISCO_MEDIO = "MÉDIO RISCO"
RISCO_BAIXO = "BAIXO RISCO"


class PredictiveRow(BaseModel):
    """Uma linha da tabela principal: um lote com cálculos de risco e perda."""
    material_code: Optional[str] = None
    material_name: Optional[str] = None  # v_df_estoque.nome_do_material_padronizado (prioridade) ou nome_do_material
    material_group: Optional[str] = None
    warehouse: Optional[str] = None
    lote: Optional[str] = None
    validity: Optional[date] = None
    days_until_expiry: Optional[int] = None
    quantity: float = 0
    unit_value: float = 0
    total_value: float = 0
    consumption_6m: float = 0
    avg_daily_consumption: float = 0  # uso interno (cálculo de risco/perda); não exibir
    avg_monthly_consumption: float = 0  # média do consumo mensal (exibida na tabela)
    last_consumption_mesano: Optional[str] = None  # mes/ano último consumo (ex.: 07/2025)
    qtde_ultimo_consumo: Optional[float] = None  # quantidade no último mes/ano com consumo
    days_stock_covers: Optional[float] = None  # dias que o estoque cobre (se consumo > 0)
    risk: str = RISCO_BAIXO
    predicted_loss_quantity: float = 0  # previsão de perda em unidades (inteiro: qtd que sobrará até a validade)
    estimated_loss: float = 0


class TopLossItem(BaseModel):
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    total_estimated_loss: float = 0


class PredictiveIndicators(BaseModel):
    """Indicadores (cards) da tela."""
    total_high_risk_value: float = Field(0, description="Soma da coluna Valor est. perda (R$), refletindo os filtros aplicados à tabela")
    loss_percentage_180d: float = Field(0, description="Estimativa percentual de perda (obedece aos filtros): valor est. perda / valor total, sobre o estoque a vencer em 180 dias")
    count_expiring_30d: int = Field(0, description="Itens vencendo em até 30 dias")
    count_no_consumption: int = Field(0, description="Materiais sem consumo nos últimos 6 meses")
    top10_loss: List[TopLossItem] = Field(default_factory=list, description="Top 10 materiais com maior valor estimado de perda")


class PredictiveResponse(BaseModel):
    filters: PredictiveFilters
    data: List[PredictiveRow]
    total_rows: int
    indicators: PredictiveIndicators
