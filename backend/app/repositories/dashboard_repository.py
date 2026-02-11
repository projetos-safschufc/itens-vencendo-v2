"""
Repositório: estoque a vencer (v_df_estoque) – 180 dias, saldo > 0, filtros UACE/ULOG.
Relacionamento: nome_do_material (parte antes do '-') = mat_cod_antigo (parte antes do '-').

Regra de validade: na tela "ITENS A VENCER" exibimos somente materiais com validade >= data atual (TODAY),
tanto no card "Próxima validade" quanto na tabela. Usamos date.today() para garantir consistência com
o calendário (não exibir itens já vencidos).
"""
from datetime import date, timedelta
from typing import Any, List, Optional

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.constants import ALL_WAREHOUSES, EXPIRY_WINDOW_DAYS, UACE_WAREHOUSES, ULOG_WAREHOUSES
from app.core.logging_config import get_logger
from app.repositories.base import execute_query, schema_prefix

logger = get_logger(__name__)

# View de estoque no schema gad_dlih_safs
# Colunas usadas: nome_do_material, validade, saldo, almoxarifado, valor_unitario (a view pode não ter "grupo")
STOCK_VIEW = "v_df_estoque"
# Se sua view tiver coluna "grupo" ou "grupo_material", defina STOCK_HAS_GRUPO = True e use e.grupo nas queries
STOCK_HAS_GRUPO = False

# Condição de validade: validade >= TODAY e < (TODAY + 180 dias). Usamos data do calendário (date.today()).
VALIDADE_ITENS_A_VENCER = "(e.validade::date) >= :today AND (e.validade::date) < :expiry_end"
VALIDADE_PARA_CARD = "(e.validade::date) >= :today AND (e.validade::date) <= :expiry_end"


def get_filter_options(
    session: Session,
    sector: Optional[str] = None,
) -> dict[str, list[str]]:
    """
    Retorna listas de almoxarifados e grupos de material para popular SELECT-BOX.
    Almoxarifados: somente a lista fixa (ALL_WAREHOUSES), restrita por setor quando UACE/ULOG.
    Grupos de material: distintos da view, restritos aos almoxarifados considerados.
    """
    sector_upper = str(sector or "").strip().upper()
    if sector_upper == "UACE":
        almoxarifados = list(UACE_WAREHOUSES)
    elif sector_upper == "ULOG":
        almoxarifados = list(ULOG_WAREHOUSES)
    else:
        almoxarifados = list(ALL_WAREHOUSES)

    s = schema_prefix(STOCK_VIEW)
    wh_clause, wh_params = _warehouse_filter(sector, None)
    today = date.today()
    params: dict[str, Any] = {
        "today": today,
        "expiry_end": today + timedelta(days=EXPIRY_WINDOW_DAYS),
        **wh_params,
    }
    base_where = f"COALESCE(e.saldo, 0) > 0 AND {VALIDADE_ITENS_A_VENCER}"
    grupos_material: list[str] = []
    try:
        grp_sql = f"""
        SELECT DISTINCT COALESCE(TRIM(e.grupo_de_material), 'Sem grupo') AS label
        FROM {s} e
        WHERE {base_where} {wh_clause}
        ORDER BY label
        """
        rows_grp = execute_query(session, grp_sql, params)
        grupos_material = [str(r.get("label", "")).strip() for r in rows_grp if r.get("label") is not None]
    except OperationalError:
        raise
    except Exception as e:
        logger.warning("dashboard_filter_options_grupos_failed", error=str(e), exc_info=True)
    return {"almoxarifados": almoxarifados, "grupos_material": grupos_material}


def _warehouse_filter(sector: Optional[str], warehouse: Optional[str]) -> tuple[str, dict]:
    """Filtro por almoxarifado. Considera somente almoxarifados da lista (ALL_WAREHOUSES)."""
    if warehouse and str(warehouse).strip():
        return " AND e.almoxarifado = :warehouse", {"warehouse": str(warehouse).strip()}
    if sector and str(sector).strip().upper() == "UACE":
        return " AND e.almoxarifado = ANY(:warehouses)", {"warehouses": UACE_WAREHOUSES}
    if sector and str(sector).strip().upper() == "ULOG":
        return " AND e.almoxarifado = ANY(:warehouses)", {"warehouses": ULOG_WAREHOUSES}
    # Sem setor/almoxarifado: restringe à lista fixa de almoxarifados considerados
    return " AND e.almoxarifado = ANY(:warehouses)", {"warehouses": ALL_WAREHOUSES}


def get_stock_expiry(
    session: Session,
    sector: Optional[str] = None,
    warehouse: Optional[str] = None,
    material_group: Optional[str] = None,
    expiry_from: Optional[date] = None,
    expiry_to: Optional[date] = None,
    material_search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[List[dict], int, dict, dict]:
    """
    Retorna (rows, total_rows, metrics_dict, charts_dict).
    Regra: exibe itens com validade >= hoje e < (hoje + 180 dias).
    Inclui itens que vencem hoje; exclui apenas validade >= (hoje + 180).
    """
    s = schema_prefix(STOCK_VIEW)
    wh_clause, wh_params = _warehouse_filter(sector, warehouse)
    today = date.today()
    params: dict[str, Any] = {
        "today": today,
        "expiry_end": today + timedelta(days=EXPIRY_WINDOW_DAYS),
        "uace_warehouses": UACE_WAREHOUSES,
        "ulog_warehouses": ULOG_WAREHOUSES,
        **wh_params,
    }
    extra = []
    if material_group and STOCK_HAS_GRUPO:
        extra.append(" AND e.grupo = :material_group")
        params["material_group"] = material_group
    if material_group and not STOCK_HAS_GRUPO:
        # Filtro por grupo de material (coluna grupo_de_material da view)
        extra.append(" AND COALESCE(TRIM(e.grupo_de_material), 'Sem grupo') = :material_group")
        params["material_group"] = str(material_group).strip()
    if expiry_from:
        effective_from = max(expiry_from, today)
        extra.append(" AND (e.validade::date) >= :expiry_from")
        params["expiry_from"] = effective_from
    if expiry_to:
        extra.append(" AND (e.validade::date) <= :expiry_to")
        params["expiry_to"] = expiry_to
    if material_search:
        extra.append(" AND (e.nome_do_material ILIKE :mat_search OR SPLIT_PART(e.nome_do_material::text, '-', 1) ILIKE :mat_search)")
        params["mat_search"] = f"%{material_search}%"
    extra_sql = "".join(extra)

    # Query principal: material_group = e.grupo se a view tiver a coluna, senão NULL
    grupo_expr = "e.grupo" if STOCK_HAS_GRUPO else "NULL::text"
    sql = f"""
    SELECT
        SPLIT_PART(e.nome_do_material::text, '-', 1) AS material_code,
        e.nome_do_material AS material_name,
        e.almoxarifado AS warehouse,
        CASE WHEN e.almoxarifado = ANY(:uace_warehouses) THEN 'UACE' WHEN e.almoxarifado = ANY(:ulog_warehouses) THEN 'ULOG' ELSE e.almoxarifado::text END AS sector,
        {grupo_expr} AS material_group,
        COALESCE(e.saldo, 0)::float AS quantity,
        COALESCE(e.valor_unitario, 0)::float AS unit_value,
        (COALESCE(e.saldo, 0) * COALESCE(e.valor_unitario, 0))::float AS total_value,
        (e.validade::date) AS expiry_date,
        ((e.validade::date) - :today) AS days_until_expiry
    FROM {s} e
    WHERE COALESCE(e.saldo, 0) > 0
      AND {VALIDADE_ITENS_A_VENCER}
      {wh_clause}
      {extra_sql}
    ORDER BY (e.validade::date) ASC, total_value DESC
    """
    count_sql = f"""
    SELECT COUNT(*) AS c FROM {s} e
    WHERE COALESCE(e.saldo, 0) > 0
      AND {VALIDADE_ITENS_A_VENCER}
      {wh_clause}
      {extra_sql}
    """
    try:
        total_result = execute_query(session, count_sql, params)
        total_rows = int(total_result[0].get("c") or 0) if total_result else 0
    except OperationalError:
        raise
    except Exception as e:
        logger.warning("dashboard_count_failed", error=str(e), exc_info=True)
        total_rows = 0
    try:
        offset = (page - 1) * page_size
        rows = execute_query(session, sql + f" LIMIT {page_size} OFFSET {offset}", params)
    except OperationalError:
        raise
    except Exception as e:
        logger.warning("dashboard_rows_failed", error=str(e), exc_info=True)
        rows = []
    # Métricas: total_value, items_count, distinct_warehouses
    metrics_sql = f"""
    SELECT
        SUM(COALESCE(e.saldo, 0) * COALESCE(e.valor_unitario, 0)) AS total_value,
        COUNT(*) AS items_count,
        COUNT(DISTINCT e.almoxarifado) AS distinct_warehouses
    FROM {s} e
    WHERE COALESCE(e.saldo, 0) > 0
      AND {VALIDADE_ITENS_A_VENCER}
      {wh_clause}
      {extra_sql}
    """
    try:
        metrics_rows = execute_query(session, metrics_sql, params)
        metrics = metrics_rows[0] if metrics_rows else {}
    except OperationalError:
        raise
    except Exception as e:
        logger.warning("dashboard_metrics_failed", error=str(e), exc_info=True)
        metrics = {}
    # Card "Próxima validade": menor data na coluna validade de v_df_estoque com validade >= hoje
    card_nearest_sql = f"""
    SELECT MIN(e.validade::date) AS nearest_expiry_date
    FROM {s} e
    WHERE COALESCE(e.saldo, 0) > 0
      AND {VALIDADE_PARA_CARD}
      {wh_clause}
      {extra_sql}
    """
    try:
        card_rows = execute_query(session, card_nearest_sql, params)
        if card_rows and card_rows[0].get("nearest_expiry_date") is not None:
            metrics["nearest_expiry_date"] = card_rows[0]["nearest_expiry_date"]
        else:
            metrics["nearest_expiry_date"] = None
    except OperationalError:
        raise
    except Exception as e:
        logger.warning("dashboard_card_nearest_failed", error=str(e), exc_info=True)
        metrics["nearest_expiry_date"] = None
    # Gráficos: valor por almoxarifado, por mês de validade, top 10 (por grupo se existir, senão por código do material)
    chart_warehouse_sql = f"""
    SELECT e.almoxarifado AS label, SUM(COALESCE(e.saldo, 0) * COALESCE(e.valor_unitario, 0))::float AS value
    FROM {s} e
    WHERE COALESCE(e.saldo, 0) > 0 AND {VALIDADE_ITENS_A_VENCER} {wh_clause} {extra_sql}
    GROUP BY e.almoxarifado ORDER BY value DESC
    """
    chart_month_sql = f"""
    SELECT TO_CHAR(e.validade, 'YYYY-MM') AS label, SUM(COALESCE(e.saldo, 0) * COALESCE(e.valor_unitario, 0))::float AS value
    FROM {s} e
    WHERE COALESCE(e.saldo, 0) > 0 AND {VALIDADE_ITENS_A_VENCER} {wh_clause} {extra_sql}
    GROUP BY TO_CHAR(e.validade, 'YYYY-MM') ORDER BY label
    """
    # Top 10 grupos de material: v_df_estoque.grupo_de_material, valor acumulado (materiais que vencem em até 180 dias)
    chart_groups_sql = f"""
    SELECT COALESCE(TRIM(e.grupo_de_material), 'Sem grupo') AS label,
           SUM(COALESCE(e.saldo, 0) * COALESCE(e.valor_unitario, 0))::float AS value
    FROM {s} e
    WHERE COALESCE(e.saldo, 0) > 0
      AND {VALIDADE_ITENS_A_VENCER}
      {wh_clause}
      {extra_sql}
    GROUP BY e.grupo_de_material
    ORDER BY value DESC
    LIMIT 10
    """
    charts = {}
    try:
        charts["value_by_warehouse"] = execute_query(session, chart_warehouse_sql, params)
        charts["value_by_expiry_month"] = execute_query(session, chart_month_sql, params)
        charts["top_material_groups"] = execute_query(session, chart_groups_sql, params)
    except OperationalError:
        raise
    except Exception as e:
        logger.warning("dashboard_charts_failed", error=str(e), exc_info=True)
    return rows, total_rows, metrics, charts
