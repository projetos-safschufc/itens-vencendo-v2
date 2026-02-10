"""
Serviço: análise preditiva por lote.
Aplica cálculos de risco e perda estimada (regras de negócio) sobre dados brutos do repositório.
"""
from datetime import date
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from app.repositories.predictive_repository import get_predictive_raw
from app.schemas.predictive import (
    PredictiveFilters,
    PredictiveIndicators,
    PredictiveResponse,
    PredictiveRow,
    RISCO_ALTO,
    RISCO_BAIXO,
    RISCO_MEDIO,
    RISCO_SEM_CONSUMO,
    TopLossItem,
)
from app.utils.cache import cache_key, get_cache
from app.utils.date_utils import business_today

DAYS_CONSUMPTION_PERIOD = 180  # 6 meses em dias (base para consumo diário nas fórmulas de risco/perda)

# Ordem de exibição da coluna Risco de Perda: do mais alto ao mais baixo (SEM CONSUMO por último)
RISK_ORDER = {RISCO_ALTO: 0, RISCO_MEDIO: 1, RISCO_BAIXO: 2, RISCO_SEM_CONSUMO: 3}


def _days_until_expiry(validity: Optional[date], today: date) -> Optional[int]:
    """
    Dias para vencer = (VALIDADE - TODAY()) em dias corridos, nunca negativo.
    Ex.: hoje 09/02, validade 28/02 → 19 dias.
    """
    if validity is None:
        return None
    delta = (validity - today).days
    return max(0, delta)


def _predicted_loss_quantity(
    media_consumo_mes: float,
    dias_ate_validade: int,
    quantidade_estoque: float,
) -> float:
    """
    Previsão de perda (em unidades), conforme regra de negócio:

    =SE(((MÉDIA_CONSUMO/30)*(VALIDADE - TODAY())) > SALDO; 0; SALDO - ((MÉDIA_CONSUMO/30)*(VALIDADE - TODAY())))

    Onde:
    - MÉDIA_CONSUMO = Consumo médio/mês (coluna "Consumo médio/mês" da tabela).
    - (VALIDADE - TODAY()) = dias até a validade (>= 0).
    - SALDO = Qtd. disponível.

    Retorno: 0 se o consumo esperado até a validade superar o estoque; senão, a sobra (estoque - consumo esperado).
    """
    consumo_ate_validade = (media_consumo_mes / 30.0) * max(0, dias_ate_validade)
    if consumo_ate_validade > quantidade_estoque:
        return 0.0
    return quantidade_estoque - consumo_ate_validade


def _risk(
    avg_daily_consumption: float,
    quantity: float,
    predicted_loss_quantity: float,
) -> str:
    """
    Risco de perda: critérios para [ALTO RISCO; MÉDIO RISCO; BAIXO RISCO; SEM CONSUMO].

    - ALTO RISCO: consumo zerado com estoque (certamente haverá perda) OU % perda >= 50%.
    - MÉDIO RISCO: % perda >= 10% e < 50%.
    - BAIXO RISCO: % perda < 10%.
    - SEM CONSUMO: consumo zerado e sem estoque (não aplicável perda).
    """
    if avg_daily_consumption == 0:
        if quantity > 0:
            return RISCO_ALTO  # tem estoque e não consome → certamente haverá perda
        return RISCO_SEM_CONSUMO  # sem estoque, sem consumo
    if quantity <= 0:
        return RISCO_BAIXO
    loss_pct = predicted_loss_quantity / quantity  # 0 a 1
    if loss_pct >= 0.5:
        return RISCO_ALTO   # 50% ou mais do estoque com previsão de perda
    if loss_pct >= 0.1:
        return RISCO_MEDIO  # entre 10% e 50%
    return RISCO_BAIXO      # menos de 10%


def _estimated_loss(
    predicted_loss_quantity: float,
    unit_value: float,
) -> float:
    """
    Valor est. perda (R$), conforme regra de negócio:

    =SE("Previsão de Perda">0; ("Previsão de Perda" * "Valor unit."); 0)

    Reflete exclusivamente o valor da previsão de perda (quantidade) × valor unitário.
    """
    if predicted_loss_quantity <= 0:
        return 0.0
    return predicted_loss_quantity * unit_value


def _format_last_mesano(raw: Any) -> Optional[str]:
    """Formata last_mesano (date ou int YYYYMM) para exibição MM/YYYY."""
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw.strftime("%m/%Y")
    try:
        yyyyymm = int(raw)
        if yyyyymm <= 0:
            return None
        month = yyyyymm % 100
        year = yyyyymm // 100
        if not (1 <= month <= 12):
            return None
        return f"{month:02d}/{year}"
    except (TypeError, ValueError):
        return None


def get_predictive_response(
    session: Session,
    filters: PredictiveFilters,
    use_cache: bool = True,
    as_of_date: Optional[date] = None,
) -> PredictiveResponse:
    """
    Data de referência para "hoje": se as_of_date for informada, usa-a para
    dias para vencer e métricas; caso contrário usa business_today().
    O frontend pode enviar a data exibida no cabeçalho para manter consistência.
    """
    stock_rows, consumption_map, last_consumption_map, avg_monthly_map = get_predictive_raw(
        session,
        sector=filters.sector,
        warehouse=filters.warehouse,
        material_group=filters.material_group,
        material_search=filters.material_search,
    )
    today = as_of_date if as_of_date is not None else business_today()
    data_dto: List[PredictiveRow] = []
    materials_with_no_consumption: set[str] = set()
    for r in stock_rows:
        material_code = (r.get("material_code") or "").strip()
        consumption_6m = consumption_map.get(material_code, 0.0)
        # Mes/ano último consumo e Qtde último consumo: vêm só do último consumo real (get_last_consumption_by_material),
        # independentes do cálculo da média (avg_monthly_map / consumo 6 meses).
        last_consumption = last_consumption_map.get(material_code) or {}
        last_mesano_str = _format_last_mesano(last_consumption.get("last_mesano"))
        qtde_ultimo = last_consumption.get("qtde_ultimo_consumo")
        qtde_ultimo_consumo = round(float(qtde_ultimo), 2) if qtde_ultimo is not None else None
        avg_daily = consumption_6m / DAYS_CONSUMPTION_PERIOD if DAYS_CONSUMPTION_PERIOD else 0.0
        # Consumo médio/mês = mesma regra da coluna "Média últimos 6 meses" (HISTÓRICO 6 MESES): soma / meses com consumo > 0
        avg_monthly = avg_monthly_map.get(material_code, 0.0)
        quantity = float(r.get("quantity") or 0)
        unit_value = float(r.get("unit_value") or 0)
        total_value = float(r.get("total_value") or 0)
        validity = r.get("validity")
        if isinstance(validity, str):
            try:
                validity = date.fromisoformat(validity[:10])
            except (ValueError, TypeError):
                validity = None
        days_until = _days_until_expiry(validity, today)
        dias_ate_validade = days_until if days_until is not None else 0
        days_stock_covers = (quantity / avg_daily) if avg_daily > 0 else None
        # Previsão de perda usa MÉDIA_CONSUMO (consumo médio/mês), não consumo/dia
        predicted_loss_quantity = _predicted_loss_quantity(avg_monthly, dias_ate_validade, quantity)
        risk = _risk(avg_daily, quantity, predicted_loss_quantity)
        estimated_loss = _estimated_loss(predicted_loss_quantity, unit_value)
        if consumption_6m == 0:
            materials_with_no_consumption.add(material_code or "")
        data_dto.append(
            PredictiveRow(
                material_code=material_code or r.get("material_name"),
                material_name=r.get("material_name"),
                material_group=r.get("material_group"),
                warehouse=r.get("warehouse"),
                lote=r.get("lote"),
                validity=validity,
                days_until_expiry=days_until,
                quantity=quantity,
                unit_value=unit_value,
                total_value=total_value,
                consumption_6m=consumption_6m,
                avg_daily_consumption=round(avg_daily, 6),
                avg_monthly_consumption=round(avg_monthly, 1),  # 1 casa decimal, mesma fonte que "Média últimos 6 meses"
                last_consumption_mesano=last_mesano_str,
                qtde_ultimo_consumo=qtde_ultimo_consumo,
                days_stock_covers=round(days_stock_covers, 2) if days_stock_covers is not None else None,
                risk=risk,
                predicted_loss_quantity=int(round(predicted_loss_quantity, 0)),
                estimated_loss=round(estimated_loss, 2),
            )
        )

    # Ordenar pela coluna Risco de Perda: do mais alto (ALTO RISCO) ao SEM CONSUMO
    data_dto.sort(key=lambda row: (RISK_ORDER.get(row.risk, 99), -float(row.estimated_loss or 0)))

    # Filtro por Risco de Perda (aplicado após ordenação; reflete na tabela e nos indicadores)
    if filters.risk and str(filters.risk).strip():
        data_dto = [r for r in data_dto if r.risk == str(filters.risk).strip()]

    # Soma da coluna "Valor est. perda (R$)" da tabela (reflete os filtros aplicados)
    total_high_risk_value = sum(row.estimated_loss for row in data_dto)
    total_value_sum = sum(float(row.total_value or 0) for row in data_dto)
    # Estimativa percentual de perda: obedece aos filtros (não é sobre todos os itens do sistema)
    loss_percentage_180d = round((total_high_risk_value / total_value_sum * 100.0), 1) if total_value_sum > 0 else 0.0
    count_expiring_30d = sum(1 for row in data_dto if row.days_until_expiry is not None and 0 <= row.days_until_expiry <= 30)
    count_no_consumption = len({row.material_code for row in data_dto if (row.consumption_6m or 0) == 0})

    # Top 10 por material (soma das perdas por lote do mesmo material)
    by_material: dict[str, tuple[str, float]] = {}
    for row in data_dto:
        key = row.material_code or row.material_name or ""
        name = row.material_name or row.material_code or "-"
        if key not in by_material:
            by_material[key] = (name, 0.0)
        by_material[key] = (name, by_material[key][1] + row.estimated_loss)
    top10 = sorted(by_material.items(), key=lambda x: -x[1][1])[:10]
    top10_loss = [TopLossItem(material_code=k, material_name=v[0], total_estimated_loss=round(v[1], 2)) for k, v in top10]

    indicators = PredictiveIndicators(
        total_high_risk_value=round(total_high_risk_value, 2),
        loss_percentage_180d=loss_percentage_180d,
        count_expiring_30d=count_expiring_30d,
        count_no_consumption=count_no_consumption,
        top10_loss=top10_loss,
    )

    resp = PredictiveResponse(
        filters=filters,
        data=data_dto,
        total_rows=len(data_dto),
        indicators=indicators,
    )
    if use_cache:
        key = cache_key("predictive", filters.sector, filters.warehouse, filters.material_group, filters.material_search, filters.risk)
        get_cache()[key] = resp
    return resp
