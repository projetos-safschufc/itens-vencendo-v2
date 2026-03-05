"""
Repositório: histórico de itens vencidos (perdas por validade).
Fonte: v_df_movimento (colunas data_movimento, quantidade, valor_unitario, almoxarifado, grupo, mat_cod_antigo)
       ou fallback df_movimento (colunas mesano, qtde_orig, valor_orig, alm_nome, nm_grupo, mat_cod_antigo).
Na coluna MATERIAL da tabela "Detalhes dos Itens Vencidos" são exibidos os dados de v_df_movimento.mat_cod_antigo
(material_name na API); no fallback para df_movimento usa-se df_movimento.mat_cod_antigo.
"""
from datetime import date
from typing import Any, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.constants import ALL_WAREHOUSES, MOVIMENTO_SUBTIPO_PERDAS_VALIDADE, UACE_WAREHOUSES, ULOG_WAREHOUSES
from app.core.logging_config import get_logger
from app.repositories.base import execute_query, schema_prefix

logger = get_logger(__name__)

MOV_VIEW = "v_df_movimento"
MOV_TABLE = "df_movimento"


def _table(session: Session) -> str:
    """Usa view se existir; senão tabela df_movimento."""
    try:
        session.execute(text(f"SELECT 1 FROM {schema_prefix(MOV_VIEW)} LIMIT 1"))
        return schema_prefix(MOV_VIEW)
    except Exception:
        return schema_prefix(MOV_TABLE)


# Ano mínimo para gráfico "perdas por ano" (exercício)
CHART_BY_YEAR_MIN_YEAR = 2023


def _build_params_and_extra(
    date_from: Optional[date],
    date_to: Optional[date],
    sector: Optional[str],
    warehouse: Optional[str],
    material_group: Optional[str],
    material: Optional[str],
    date_col: str,
    wh_col: str,
    grp_col: str,
    qty_col: str,
    skip_dates: bool = False,
) -> tuple[dict, str]:
    """Monta params e cláusulas WHERE; date_col/wh_col/grp_col/qty_col variam entre view e tabela. skip_dates=True omite filtro de período (para chart by_year)."""
    params: dict[str, Any] = {"subtipo": MOVIMENTO_SUBTIPO_PERDAS_VALIDADE}
    extra = []
    if not skip_dates:
        if date_from:
            extra.append(f" AND m.{date_col} >= :date_from")
            params["date_from"] = date_from
        if date_to:
            extra.append(f" AND m.{date_col} <= :date_to")
            params["date_to"] = date_to
    if warehouse:
        extra.append(f" AND m.{wh_col} = :warehouse")
        params["warehouse"] = warehouse
    if material_group:
        params["material_group"] = material_group
    if material:
        extra.append(" AND (m.mat_cod_antigo ILIKE :mat OR SPLIT_PART(m.mat_cod_antigo::text, '-', 1) ILIKE :mat)")
        params["mat"] = f"%{material}%"
    if sector and str(sector).strip().upper() == "UACE":
        extra.append(f" AND m.{wh_col} = ANY(:sector_warehouses)")
        params["sector_warehouses"] = UACE_WAREHOUSES
    elif sector and str(sector).strip().upper() == "ULOG":
        extra.append(f" AND m.{wh_col} = ANY(:sector_warehouses)")
        params["sector_warehouses"] = ULOG_WAREHOUSES
    else:
        extra.append(f" AND m.{wh_col} = ANY(:sector_warehouses)")
        params["sector_warehouses"] = ALL_WAREHOUSES
    if material_group:
        extra.append(f" AND COALESCE(TRIM(m.{grp_col}), 'Sem grupo') = :material_group")
    return params, "".join(extra)


def get_expired_items(
    session: Session,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    year: Optional[int] = None,
    sector: Optional[str] = None,
    warehouse: Optional[str] = None,
    material_group: Optional[str] = None,
    material: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[List[dict], int, dict, dict]:
    """
    Retorna (rows, total_rows, metrics, charts).
    year: quando informado, define período 01/01 a 31/12 desse ano.
    Tenta v_df_movimento; se falhar, usa df_movimento.
    """
    if year is not None and year >= CHART_BY_YEAR_MIN_YEAR:
        date_from = date(year, 1, 1)
        date_to = date(year, 12, 31)

    # Params/extra para chart "perdas por ano" (sem filtro de período; desde 2023)
    params_yearly, extra_yearly = _build_params_and_extra(
        None, None, sector, warehouse, material_group, material,
        "data_movimento", "almoxarifado", "grupo", "quantidade",
        skip_dates=True,
    )
    params_yearly["min_year"] = CHART_BY_YEAR_MIN_YEAR

    # 1) Tentar view v_df_movimento
    tbl_view = schema_prefix(MOV_VIEW)
    params, extra_sql = _build_params_and_extra(
        date_from, date_to, sector, warehouse, material_group, material,
        "data_movimento", "almoxarifado", "grupo", "quantidade",
    )
    rows, total_rows, metrics, charts = _run_queries_view(
        session, tbl_view, params, extra_sql, page, page_size,
        params_yearly=params_yearly, extra_yearly=extra_yearly,
        date_col="data_movimento", val_expr="(COALESCE(m.quantidade, 0) * COALESCE(m.valor_unitario, 0))::float",
        qty_cond="COALESCE(m.quantidade, 0) > 0",
    )
    if rows is not None:
        return rows, total_rows, metrics, charts

    session.rollback()
    # 2) Fallback: tabela df_movimento (mesano, qtde_orig, valor_orig, alm_nome, nm_grupo)
    tbl_table = schema_prefix(MOV_TABLE)
    params_yearly_t, extra_yearly_t = _build_params_and_extra(
        None, None, sector, warehouse, material_group, material,
        "mesano", "alm_nome", "nm_grupo", "qtde_orig",
        skip_dates=True,
    )
    params_yearly_t["min_year"] = CHART_BY_YEAR_MIN_YEAR
    params, extra_sql = _build_params_and_extra(
        date_from, date_to, sector, warehouse, material_group, material,
        "mesano", "alm_nome", "nm_grupo", "qtde_orig",
    )
    return _run_queries_table(
        session, tbl_table, params, extra_sql, page, page_size,
        params_yearly=params_yearly_t, extra_yearly=extra_yearly_t,
        date_col="mesano", val_expr="COALESCE(m.valor_orig, 0)::float",
        qty_cond="COALESCE(m.qtde_orig, 0) > 0",
    )


def _run_queries_view(
    session: Session,
    tbl: str,
    params: dict,
    extra_sql: str,
    page: int,
    page_size: int,
    *,
    params_yearly: Optional[dict] = None,
    extra_yearly: Optional[str] = None,
    date_col: str = "data_movimento",
    val_expr: str = "(COALESCE(m.quantidade, 0) * COALESCE(m.valor_unitario, 0))::float",
    qty_cond: str = "COALESCE(m.quantidade, 0) > 0",
) -> tuple[List[dict] | None, int, dict, dict]:
    """Executa queries usando colunas da view (data_movimento, quantidade, valor_unitario, almoxarifado, grupo, mat_cod_antigo)."""
    # Coluna Material da tabela = v_df_movimento.mat_cod_antigo (material_name)
    sql = f"""
    SELECT
        SPLIT_PART(m.mat_cod_antigo::text, '-', 1) AS material_code,
        m.mat_cod_antigo AS material_name,
        m.almoxarifado AS warehouse,
        COALESCE(TRIM(m.grupo), 'Sem grupo') AS group_name,
        m.data_movimento AS movement_date,
        COALESCE(m.quantidade, 0)::float AS quantity,
        CASE WHEN COALESCE(m.quantidade, 0) > 0
             THEN (COALESCE(m.quantidade, 0) * COALESCE(m.valor_unitario, 0))::float / NULLIF(m.quantidade, 0)
             ELSE 0 END AS unit_value,
        (COALESCE(m.quantidade, 0) * COALESCE(m.valor_unitario, 0))::float AS total_value
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo
      AND COALESCE(m.quantidade, 0) > 0
      {extra_sql}
    ORDER BY m.data_movimento DESC, m.almoxarifado, m.grupo
    """
    count_sql = f"""
    SELECT COUNT(*) AS c FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.quantidade, 0) > 0
      {extra_sql}
    """
    try:
        tr = execute_query(session, count_sql, params)
        total_rows = int(tr[0].get("c", 0) or 0)
    except Exception as e:
        session.rollback()
        logger.warning("expired_repository_view_count_failed", error=str(e), table=tbl)
        return None, 0, {}, {}

    try:
        offset = (page - 1) * page_size
        rows = execute_query(session, sql + f" LIMIT {page_size} OFFSET {offset}", params)
    except Exception as e:
        session.rollback()
        logger.warning("expired_repository_view_rows_failed", error=str(e), table=tbl)
        return None, 0, {}, {}

    metrics_sql = f"""
    SELECT
        SUM(COALESCE(m.quantidade, 0) * COALESCE(m.valor_unitario, 0))::float AS total_lost_value,
        COUNT(*) AS total_expired_items
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.quantidade, 0) > 0
      {extra_sql}
    """
    metrics = {}
    try:
        mr = execute_query(session, metrics_sql, params)
        if mr:
            total_lost = float(mr[0].get("total_lost_value") or 0)
            count = int(mr[0].get("total_expired_items") or 0)
            metrics = {
                "total_lost_value": total_lost,
                "total_expired_items": count,
                "average_loss_per_item": total_lost / count if count else 0,
            }
    except Exception as e:
        session.rollback()
        logger.warning("expired_repository_view_metrics_failed", error=str(e))

    chart_month_sql = f"""
    SELECT TO_CHAR(m.data_movimento, 'YYYY-MM') AS month, SUM(COALESCE(m.quantidade, 0) * COALESCE(m.valor_unitario, 0))::float AS value
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.quantidade, 0) > 0 {extra_sql}
    GROUP BY TO_CHAR(m.data_movimento, 'YYYY-MM') ORDER BY month
    """
    chart_group_sql = f"""
    SELECT COALESCE(TRIM(m.grupo), 'Sem grupo') AS label, SUM(COALESCE(m.quantidade, 0) * COALESCE(m.valor_unitario, 0))::float AS value
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.quantidade, 0) > 0 {extra_sql}
    GROUP BY COALESCE(TRIM(m.grupo), 'Sem grupo') ORDER BY value DESC LIMIT 10
    """
    chart_wh_sql = f"""
    SELECT m.almoxarifado AS label, SUM(COALESCE(m.quantidade, 0) * COALESCE(m.valor_unitario, 0))::float AS value
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.quantidade, 0) > 0 {extra_sql}
    GROUP BY m.almoxarifado ORDER BY value DESC
    """
    chart_distinct_sql = f"""
    SELECT TO_CHAR(m.data_movimento, 'YYYY-MM') AS month, COUNT(DISTINCT SPLIT_PART(m.mat_cod_antigo::text, '-', 1)) AS count
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.quantidade, 0) > 0 {extra_sql}
    GROUP BY TO_CHAR(m.data_movimento, 'YYYY-MM') ORDER BY month
    """
    charts = {}
    try:
        charts["monthly_series"] = execute_query(session, chart_month_sql, params)
        charts["by_group"] = execute_query(session, chart_group_sql, params)
        charts["by_warehouse"] = execute_query(session, chart_wh_sql, params)
        charts["distinct_materials_per_month"] = execute_query(session, chart_distinct_sql, params)
        if params_yearly is not None and extra_yearly is not None:
            chart_by_year_sql = f"""
            SELECT EXTRACT(YEAR FROM m.{date_col})::int AS year, SUM({val_expr}) AS value
            FROM {tbl} m
            WHERE m.movimento_subtipo = :subtipo AND {qty_cond}
              AND EXTRACT(YEAR FROM m.{date_col}) >= :min_year {extra_yearly}
            GROUP BY EXTRACT(YEAR FROM m.{date_col}) ORDER BY year
            """
            charts["by_year"] = execute_query(session, chart_by_year_sql, params_yearly)
        else:
            charts["by_year"] = []
    except Exception as e:
        session.rollback()
        logger.warning("expired_repository_view_charts_failed", error=str(e))
    return rows, total_rows, metrics, charts


def _run_queries_table(
    session: Session,
    tbl: str,
    params: dict,
    extra_sql: str,
    page: int,
    page_size: int,
    *,
    params_yearly: Optional[dict] = None,
    extra_yearly: Optional[str] = None,
    date_col: str = "mesano",
    val_expr: str = "COALESCE(m.valor_orig, 0)::float",
    qty_cond: str = "COALESCE(m.qtde_orig, 0) > 0",
) -> tuple[List[dict], int, dict, dict]:
    """Executa queries usando colunas da tabela df_movimento (mesano, qtde_orig, valor_orig, alm_nome, nm_grupo, mat_cod_antigo)."""
    # Coluna Material da tabela = df_movimento.mat_cod_antigo (material_name)
    sql = f"""
    SELECT
        SPLIT_PART(m.mat_cod_antigo::text, '-', 1) AS material_code,
        m.mat_cod_antigo AS material_name,
        m.alm_nome AS warehouse,
        COALESCE(TRIM(m.nm_grupo), 'Sem grupo') AS group_name,
        m.mesano AS movement_date,
        COALESCE(m.qtde_orig, 0)::float AS quantity,
        CASE WHEN COALESCE(m.qtde_orig, 0) > 0
             THEN COALESCE(m.valor_orig, 0)::float / NULLIF(m.qtde_orig, 0)
             ELSE 0 END AS unit_value,
        COALESCE(m.valor_orig, 0)::float AS total_value
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo
      AND COALESCE(m.qtde_orig, 0) > 0
      {extra_sql}
    ORDER BY m.mesano DESC, m.alm_nome, m.nm_grupo
    """
    count_sql = f"""
    SELECT COUNT(*) AS c FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.qtde_orig, 0) > 0
      {extra_sql}
    """
    try:
        tr = execute_query(session, count_sql, params)
        total_rows = int(tr[0].get("c", 0) or 0)
    except Exception as e:
        session.rollback()
        logger.warning("expired_repository_table_count_failed", error=str(e), table=tbl)
        return [], 0, {}, {}

    try:
        offset = (page - 1) * page_size
        rows = execute_query(session, sql + f" LIMIT {page_size} OFFSET {offset}", params)
    except Exception as e:
        session.rollback()
        logger.warning("expired_repository_table_rows_failed", error=str(e), table=tbl)
        return [], 0, {}, {}

    metrics_sql = f"""
    SELECT
        SUM(COALESCE(m.valor_orig, 0))::float AS total_lost_value,
        COUNT(*) AS total_expired_items
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.qtde_orig, 0) > 0
      {extra_sql}
    """
    metrics = {}
    try:
        mr = execute_query(session, metrics_sql, params)
        if mr:
            total_lost = float(mr[0].get("total_lost_value") or 0)
            count = int(mr[0].get("total_expired_items") or 0)
            metrics = {
                "total_lost_value": total_lost,
                "total_expired_items": count,
                "average_loss_per_item": total_lost / count if count else 0,
            }
    except Exception as e:
        session.rollback()
        logger.warning("expired_repository_table_metrics_failed", error=str(e))

    chart_month_sql = f"""
    SELECT TO_CHAR(m.mesano, 'YYYY-MM') AS month, SUM(COALESCE(m.valor_orig, 0))::float AS value
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.qtde_orig, 0) > 0 {extra_sql}
    GROUP BY TO_CHAR(m.mesano, 'YYYY-MM') ORDER BY month
    """
    chart_group_sql = f"""
    SELECT COALESCE(TRIM(m.nm_grupo), 'Sem grupo') AS label, SUM(COALESCE(m.valor_orig, 0))::float AS value
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.qtde_orig, 0) > 0 {extra_sql}
    GROUP BY COALESCE(TRIM(m.nm_grupo), 'Sem grupo') ORDER BY value DESC LIMIT 10
    """
    chart_wh_sql = f"""
    SELECT m.alm_nome AS label, SUM(COALESCE(m.valor_orig, 0))::float AS value
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.qtde_orig, 0) > 0 {extra_sql}
    GROUP BY m.alm_nome ORDER BY value DESC
    """
    chart_distinct_sql = f"""
    SELECT TO_CHAR(m.mesano, 'YYYY-MM') AS month, COUNT(DISTINCT SPLIT_PART(m.mat_cod_antigo::text, '-', 1)) AS count
    FROM {tbl} m
    WHERE m.movimento_subtipo = :subtipo AND COALESCE(m.qtde_orig, 0) > 0 {extra_sql}
    GROUP BY TO_CHAR(m.mesano, 'YYYY-MM') ORDER BY month
    """
    charts = {}
    try:
        charts["monthly_series"] = execute_query(session, chart_month_sql, params)
        charts["by_group"] = execute_query(session, chart_group_sql, params)
        charts["by_warehouse"] = execute_query(session, chart_wh_sql, params)
        charts["distinct_materials_per_month"] = execute_query(session, chart_distinct_sql, params)
        if params_yearly is not None and extra_yearly is not None:
            chart_by_year_sql = f"""
            SELECT EXTRACT(YEAR FROM m.{date_col})::int AS year, SUM({val_expr}) AS value
            FROM {tbl} m
            WHERE m.movimento_subtipo = :subtipo AND {qty_cond}
              AND EXTRACT(YEAR FROM m.{date_col}) >= :min_year {extra_yearly}
            GROUP BY EXTRACT(YEAR FROM m.{date_col}) ORDER BY year
            """
            charts["by_year"] = execute_query(session, chart_by_year_sql, params_yearly)
        else:
            charts["by_year"] = []
    except Exception as e:
        session.rollback()
        logger.warning("expired_repository_table_charts_failed", error=str(e))
    return rows, total_rows, metrics, charts


def get_expired_filter_options(
    session: Session,
    sector: Optional[str] = None,
) -> dict:
    """Retorna listas de almoxarifados e grupos de material para filtros. Tenta view, depois tabela."""
    params: dict[str, Any] = {"subtipo": MOVIMENTO_SUBTIPO_PERDAS_VALIDADE}
    if sector and str(sector).strip().upper() == "UACE":
        params["sector_warehouses"] = UACE_WAREHOUSES
    elif sector and str(sector).strip().upper() == "ULOG":
        params["sector_warehouses"] = ULOG_WAREHOUSES
    else:
        params["sector_warehouses"] = ALL_WAREHOUSES

    # Tentar view
    tbl_view = schema_prefix(MOV_VIEW)
    extra_view = " AND m.almoxarifado = ANY(:sector_warehouses) AND COALESCE(m.quantidade, 0) > 0"
    try:
        wh_sql = f"""
        SELECT DISTINCT m.almoxarifado AS value FROM {tbl_view} m
        WHERE m.movimento_subtipo = :subtipo {extra_view}
        ORDER BY value
        """
        gr_sql = f"""
        SELECT DISTINCT COALESCE(TRIM(m.grupo), 'Sem grupo') AS value FROM {tbl_view} m
        WHERE m.movimento_subtipo = :subtipo {extra_view}
        ORDER BY value
        """
        warehouses = [r["value"] for r in execute_query(session, wh_sql, params) if r.get("value")]
        material_groups = [r["value"] for r in execute_query(session, gr_sql, params) if r.get("value")]
        return {"warehouses": warehouses, "material_groups": material_groups}
    except Exception as e:
        session.rollback()
        logger.warning("expired_filter_options_view_failed", error=str(e))

    # Fallback: tabela df_movimento
    tbl_table = schema_prefix(MOV_TABLE)
    extra_table = " AND m.alm_nome = ANY(:sector_warehouses) AND COALESCE(m.qtde_orig, 0) > 0"
    warehouses = []
    material_groups = []
    try:
        wh_sql = f"""
        SELECT DISTINCT m.alm_nome AS value FROM {tbl_table} m
        WHERE m.movimento_subtipo = :subtipo {extra_table}
        ORDER BY value
        """
        warehouses = [r["value"] for r in execute_query(session, wh_sql, params) if r.get("value")]
    except Exception as e:
        session.rollback()
        logger.warning("expired_filter_options_table_warehouses_failed", error=str(e))
    try:
        gr_sql = f"""
        SELECT DISTINCT COALESCE(TRIM(m.nm_grupo), 'Sem grupo') AS value FROM {tbl_table} m
        WHERE m.movimento_subtipo = :subtipo {extra_table}
        ORDER BY value
        """
        material_groups = [r["value"] for r in execute_query(session, gr_sql, params) if r.get("value")]
    except Exception as e:
        session.rollback()
        logger.warning("expired_filter_options_table_groups_failed", error=str(e))
    return {"warehouses": warehouses, "material_groups": material_groups}
