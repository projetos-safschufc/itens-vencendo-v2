"""
DTOs para a aba TESTE (média últimos 6 meses por material + consumo por mês).
"""
from typing import List, Optional

from pydantic import BaseModel


class TesteRow(BaseModel):
    material: str = ""
    media_ultimos_6_meses: float = 0.0
    # Consumo por mês: M-6, M-5, M-4, M-3, M-2, M-1, Mês Atual (índices 0..6)
    consumo_m_6: Optional[float] = None
    consumo_m_5: Optional[float] = None
    consumo_m_4: Optional[float] = None
    consumo_m_3: Optional[float] = None
    consumo_m_2: Optional[float] = None
    consumo_m_1: Optional[float] = None
    consumo_mes_atual: Optional[float] = None


class TesteResponse(BaseModel):
    data: List[TesteRow]
    total_rows: int
    # Cabeçalhos dinâmicos das 7 colunas (M-6 até Mês Atual), ex.: ["Ago/2026", "Set/2026", ..., "Mês Atual (fev/2026)"]
    month_labels: List[str] = []
