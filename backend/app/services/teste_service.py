"""
Serviço: aba TESTE – média dos últimos 6 meses por material + consumo por mês (7 colunas dinâmicas).
"""
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.repositories.teste_repository import (
    get_teste_consumo_por_mesano,
    get_teste_media_6m,
    _seven_months_ref,
)
from app.schemas.teste import TesteResponse, TesteRow

logger = get_logger(__name__)

MESES_ABREV = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]


def _month_labels(month_refs: List[Tuple[int, int]]) -> List[str]:
    """Gera 7 rótulos: M-6..M-5 com 'Abr/2026', último com 'Mês Atual (fev/2026)'."""
    labels = []
    for i, (y, m) in enumerate(month_refs):
        abrev = MESES_ABREV[m - 1] if 1 <= m <= 12 else str(m)
        if i < 6:
            labels.append(f"{abrev}/{y}")
        else:
            labels.append(f"Mês Atual ({abrev.lower()}/{y})")
    return labels


def get_default_month_labels() -> List[str]:
    """Retorna os rótulos dos 7 meses (M-6 até Mês Atual) para uso em respostas fallback."""
    return _month_labels(_seven_months_ref())


def get_teste_response(session: Session, material: Optional[str] = None) -> TesteResponse:
    month_refs = _seven_months_ref()
    month_labels = _month_labels(month_refs)
    mesano_ints = [y * 100 + m for y, m in month_refs]

    # Lista base de materiais e média (sempre da mesma fonte que já funciona na tela)
    rows_legacy = get_teste_media_6m(session, material=material)

    # Consumo por (material, mesano) nos 7 meses – enriquece as colunas mensais (não propaga falha para não gerar 503)
    try:
        consumo_rows = get_teste_consumo_por_mesano(session, material=material, month_refs=month_refs)
    except Exception as e:
        logger.warning("teste_consumo_por_mesano_fallback", error=str(e), material_filter=material)
        consumo_rows = []

    # Pivot: material_code -> (material_display, [c0, c1, ..., c6])
    by_material: Dict[str, Tuple[str, List[float]]] = {}
    for r in consumo_rows:
        code = (r.get("material_code") or "").strip()
        mat_display = (r.get("material") or code).strip()
        yyyyymm = r.get("mesano_yyyymm")
        consumo = float(r.get("consumo") or 0)
        if not code:
            continue
        try:
            idx = mesano_ints.index(int(yyyyymm))
        except (ValueError, TypeError):
            continue
        if code not in by_material:
            by_material[code] = (mat_display, [0.0] * 7)
        by_material[code][1][idx] = consumo

    # Uma linha por material da lista legacy; 7 colunas preenchidas do pivot quando existir.
    # Ignora linhas com Material vazio (ex.: agrupamento de movimentos com mat_cod_antigo nulo).
    data: List[TesteRow] = []
    for r in rows_legacy:
        mat_display = str(r.get("material") or r.get("MATERIAL") or "").strip()
        if not mat_display:
            continue
        media_legacy = float(r.get("media_ultimos_6_meses") or r.get("MEDIA_ULTIMOS_6_MESES") or 0)
        code = (mat_display.split("-", 1)[0].strip() if "-" in mat_display else mat_display) or ""
        if not code:
            continue

        if code in by_material:
            _, cols = by_material[code]
            # Média real: só meses com consumo > 0 (soma / quantidade de meses com consumo)
            consumos_positivos = [c for c in cols[0:6] if (c or 0) > 0]
            total = sum(consumos_positivos)
            qtd_meses_com_consumo = len(consumos_positivos)
            media = round(total / qtd_meses_com_consumo, 2) if qtd_meses_com_consumo > 0 else 0.0
            data.append(
                TesteRow(
                    material=mat_display,
                    media_ultimos_6_meses=media,
                    consumo_m_6=round(cols[0], 2),
                    consumo_m_5=round(cols[1], 2),
                    consumo_m_4=round(cols[2], 2),
                    consumo_m_3=round(cols[3], 2),
                    consumo_m_2=round(cols[4], 2),
                    consumo_m_1=round(cols[5], 2),
                    consumo_mes_atual=round(cols[6], 2),
                )
            )
        else:
            data.append(
                TesteRow(
                    material=mat_display,
                    media_ultimos_6_meses=media_legacy,
                    consumo_m_6=None,
                    consumo_m_5=None,
                    consumo_m_4=None,
                    consumo_m_3=None,
                    consumo_m_2=None,
                    consumo_m_1=None,
                    consumo_mes_atual=None,
                )
            )

    return TesteResponse(data=data, total_rows=len(data), month_labels=month_labels)
