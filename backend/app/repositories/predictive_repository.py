"""
Repositório: análise preditiva (READ-ONLY).
Base: v_df_estoque (estoque por lote, 180 dias) + consumo dos últimos 6 meses (mesma lógica da tela TESTE).
Na coluna MATERIAL da tabela são exibidos os dados de v_df_estoque.nome_do_material_padronizado (prioridade),
com fallback para nome_do_material quando a view não tiver a coluna padronizada.
Relacionamento estoque × movimento (para consumo/média): código = parte antes do '-' em ambos.
Consumo: get_teste_media_6m (v_df_movimento/df_movimento; RM, qtde>0, 6 meses anteriores ao mês atual).
Último consumo: get_last_consumption_by_material (last_mesano, qtde_ultimo_consumo por material).
Cada LOTE é uma unidade de análise. Cálculos de risco e perda na aplicação.
"""
from datetime import date as date_type, timedelta
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from app.constants import (
    ALL_WAREHOUSES,
    EXPIRY_WINDOW_DAYS,
    UACE_WAREHOUSES,
    ULOG_WAREHOUSES,
)
from app.core.logging_config import get_logger
from app.repositories.base import execute_query, schema_prefix
from app.repositories.teste_repository import get_teste_media_6m
from app.utils.date_utils import business_today

logger = get_logger(__name__)


def _last_mesano_in_6m_window(last_mesano: Any, today: date_type) -> bool:
    """
    Verifica se last_mesano (date ou int YYYYMM) está na janela dos 6 meses anteriores ao mês atual
    (mês atual excluído): >= (mês atual - 6 meses) e < mês atual.
    """
    if last_mesano is None:
        return False
    try:
        if isinstance(last_mesano, date_type):
            y, m = last_mesano.year, last_mesano.month
            yyyyymm = y * 100 + m
        else:
            yyyyymm = int(last_mesano)
        current_y = today.year
        current_m = today.month
        current_yyyymm = current_y * 100 + current_m
        # Início da janela: mês atual - 6 meses
        total_months = current_y * 12 + current_m - 6
        start_y = total_months // 12
        start_m = total_months % 12
        if start_m == 0:
            start_m = 12
            start_y -= 1
        start_yyyymm = start_y * 100 + start_m
        return start_yyyymm <= yyyyymm < current_yyyymm
    except (TypeError, ValueError):
        return False


STOCK_VIEW = "v_df_estoque"
MOV_VIEW = "v_df_movimento"
MOVIMENTO_CONSUMO = "RM"
# Se v_df_estoque não tiver coluna lote, use HAS_LOTE = False para fallback (lote exibido como vazio)
HAS_LOTE = True


def _warehouse_clause(sector: Optional[str], warehouse: Optional[str]) -> tuple[str, dict]:
    """
    Monta a cláusula SQL e os parâmetros para filtrar estoque por almoxarifado.
    Se warehouse for informado, filtra por esse almoxarifado; se sector for UACE ou ULOG,
    usa a lista fixa de almoxarifados do setor; caso contrário, usa ALL_WAREHOUSES.
    Retorna (fragmento WHERE, dict de parâmetros).
    """
    if warehouse and str(warehouse).strip():
        return " AND e.almoxarifado = :warehouse", {"warehouse": str(warehouse).strip()}
    if sector and str(sector).strip().upper() == "UACE":
        return " AND e.almoxarifado = ANY(:warehouses)", {"warehouses": UACE_WAREHOUSES}
    if sector and str(sector).strip().upper() == "ULOG":
        return " AND e.almoxarifado = ANY(:warehouses)", {"warehouses": ULOG_WAREHOUSES}
    return " AND e.almoxarifado = ANY(:warehouses)", {"warehouses": ALL_WAREHOUSES}


def _stock_select_lote() -> str:
    """
    Retorna a expressão SQL para a coluna de lote na consulta de estoque.
    Se a view v_df_estoque tiver coluna lote (HAS_LOTE=True), usa e.lote; senão retorna literal vazio.
    """
    if HAS_LOTE:
        return "COALESCE(TRIM(CAST(e.lote AS TEXT)), '') AS lote"
    return "'' AS lote"


def get_last_consumption_by_material(session: Session) -> dict[str, dict]:
    """
    Obtém o último mês/ano com consumo e a quantidade consumida por material (código).

    Fonte: v_df_movimento (movimento RM, qtde_orig > 0). Não aplica janela de 6 meses nem
    exclusão do mês atual: considera todo o histórico e retorna o mês mais recente com consumo
    (incluindo o mês atual). Cálculo independente da média de consumo (get_teste_media_6m).
    Tenta primeiro mesano como date; em falha, mesano como inteiro YYYYMM.
    Retorna: dict[material_code] -> {"last_mesano": date ou int YYYYMM, "qtde_ultimo_consumo": float}.
    Usado na análise preditiva para exibir "Mes/ano último consumo" e "Qtde último consumo".
    """
    mov = schema_prefix(MOV_VIEW)
    mov_cond = "COALESCE(m.movimento_cd, m.movimento_subtipo, '') = :movimento_consumo"
    ref = "TRIM(SPLIT_PART(m.mat_cod_antigo::text, '-', 1))"
    out: dict[str, dict] = {}

    # Tentativa 1: mesano como date (sem filtrar por mês atual = último consumo real)
    sql_date = f"""
    WITH agg AS (
      SELECT {ref} AS material_code, m.mesano, SUM(COALESCE(m.qtde_orig, 0)) AS qtde
      FROM {mov} m
      WHERE {mov_cond} AND COALESCE(m.qtde_orig, 0) > 0
      GROUP BY {ref}, m.mesano
    ),
    ranked AS (
      SELECT material_code, mesano, qtde,
             ROW_NUMBER() OVER (PARTITION BY material_code ORDER BY mesano DESC) AS rn
      FROM agg
    )
    SELECT material_code, mesano AS last_mesano, qtde AS qtde_ultimo_consumo
    FROM ranked WHERE rn = 1
    """
    try:
        params = {"movimento_consumo": MOVIMENTO_CONSUMO}
        rows = execute_query(session, sql_date, params)
        for r in rows:
            code = (r.get("material_code") or "").strip()
            if not code:
                continue
            out[code] = {
                "last_mesano": r.get("last_mesano"),
                "qtde_ultimo_consumo": float(r.get("qtde_ultimo_consumo") or 0),
            }
        if out:
            return out
    except Exception as e:
        logger.warning("predictive last_consumption (mesano date) failed", error=str(e))
        session.rollback()

    # Tentativa 2: mesano como inteiro YYYYMM (sem filtrar por mês atual = último consumo real)
    sql_int = f"""
    WITH agg AS (
      SELECT {ref} AS material_code, m.mesano, SUM(COALESCE(m.qtde_orig, 0)) AS qtde
      FROM {mov} m
      WHERE {mov_cond} AND COALESCE(m.qtde_orig, 0) > 0
      GROUP BY {ref}, m.mesano
    ),
    ranked AS (
      SELECT material_code, mesano, qtde,
             ROW_NUMBER() OVER (PARTITION BY material_code ORDER BY mesano DESC) AS rn
      FROM agg
    )
    SELECT material_code, mesano AS last_mesano, qtde AS qtde_ultimo_consumo
    FROM ranked WHERE rn = 1
    """
    try:
        params = {"movimento_consumo": MOVIMENTO_CONSUMO}
        rows = execute_query(session, sql_int, params)
        for r in rows:
            code = (r.get("material_code") or "").strip()
            if not code:
                continue
            out[code] = {
                "last_mesano": r.get("last_mesano"),
                "qtde_ultimo_consumo": float(r.get("qtde_ultimo_consumo") or 0),
            }
        return out
    except Exception as e:
        logger.warning("predictive last_consumption (mesano int) failed", error=str(e))
        session.rollback()

    # Tentativa 3: view com data_movimento e quantidade (estilo view, sem mesano/qtde_orig)
    if not out:
        sql_view = f"""
        WITH agg AS (
          SELECT {ref} AS material_code,
                 date_trunc('month', m.data_movimento)::date AS mesano,
                 SUM(COALESCE(m.quantidade, 0)) AS qtde
          FROM {mov} m
          WHERE COALESCE(m.movimento_cd, m.movimento_subtipo, '') = :movimento_consumo
            AND COALESCE(m.quantidade, 0) > 0
          GROUP BY {ref}, date_trunc('month', m.data_movimento)
        ),
        ranked AS (
          SELECT material_code, mesano, qtde,
                 ROW_NUMBER() OVER (PARTITION BY material_code ORDER BY mesano DESC) AS rn
          FROM agg
        )
        SELECT material_code, mesano AS last_mesano, qtde AS qtde_ultimo_consumo
        FROM ranked WHERE rn = 1
        """
        try:
            params = {"movimento_consumo": MOVIMENTO_CONSUMO}
            rows = execute_query(session, sql_view, params)
            for r in rows:
                code = (r.get("material_code") or "").strip()
                if not code:
                    continue
                out[code] = {
                    "last_mesano": r.get("last_mesano"),
                    "qtde_ultimo_consumo": float(r.get("qtde_ultimo_consumo") or 0),
                }
        except Exception as e:
            logger.warning("predictive last_consumption (data_movimento view) failed", error=str(e))
            session.rollback()

    return out


def _run_stock_query(
    session: Session,
    s_stock: str,
    wh_clause: str,
    extra_stock_base: List[str],
    lote_expr: str,
    params: dict,
    material_search: Optional[str] = None,
) -> List[dict]:
    """
    Executa a consulta de estoque. Prioriza nome_do_material_padronizado para a coluna MATERIAL (exibição);
    fallback para nome_do_material se a view não tiver padronizado. material_code continua pela parte antes do '-'.
    """
    for material_col in ("nome_do_material_padronizado", "nome_do_material"):
        extra_sql = "".join(extra_stock_base)
        if material_search:
            extra_sql += f" AND (e.{material_col} ILIKE :mat_search OR SPLIT_PART(e.{material_col}::text, '-', 1) ILIKE :mat_search)"
        sql = f"""
    SELECT
        TRIM(SPLIT_PART(e.{material_col}::text, '-', 1)) AS material_code,
        e.{material_col} AS material_name,
        e.almoxarifado AS warehouse,
        COALESCE(TRIM(e.grupo_de_material), 'Sem grupo') AS material_group,
        {lote_expr},
        (e.validade::date) AS validity,
        COALESCE(e.saldo, 0)::float AS quantity,
        COALESCE(e.valor_unitario, 0)::float AS unit_value,
        (COALESCE(e.saldo, 0) * COALESCE(e.valor_unitario, 0))::float AS total_value
    FROM {s_stock} e
    WHERE COALESCE(e.saldo, 0) > 0
      AND (e.validade::date) >= :today AND (e.validade::date) < :expiry_end
      {wh_clause}
      {extra_sql}
    ORDER BY (e.validade::date) ASC, (COALESCE(e.saldo, 0) * COALESCE(e.valor_unitario, 0)) DESC
    """
        try:
            return execute_query(session, sql, params)
        except Exception as e:
            logger.warning(
                "predictive stock query failed with column %s, trying fallback",
                material_col,
                error=str(e),
            )
            session.rollback()
    # Fallback sem coluna lote (se HAS_LOTE e view não tiver lote)
    if HAS_LOTE:
        material_col = "nome_do_material_padronizado"
        extra_sql = "".join(extra_stock_base)
        if material_search:
            extra_sql += f" AND (e.{material_col} ILIKE :mat_search OR SPLIT_PART(e.{material_col}::text, '-', 1) ILIKE :mat_search)"
        sql = f"""
    SELECT
        TRIM(SPLIT_PART(e.{material_col}::text, '-', 1)) AS material_code,
        e.{material_col} AS material_name,
        e.almoxarifado AS warehouse,
        COALESCE(TRIM(e.grupo_de_material), 'Sem grupo') AS material_group,
        '' AS lote,
        (e.validade::date) AS validity,
        COALESCE(e.saldo, 0)::float AS quantity,
        COALESCE(e.valor_unitario, 0)::float AS unit_value,
        (COALESCE(e.saldo, 0) * COALESCE(e.valor_unitario, 0))::float AS total_value
    FROM {s_stock} e
    WHERE COALESCE(e.saldo, 0) > 0
      AND (e.validade::date) >= :today AND (e.validade::date) < :expiry_end
      {wh_clause}
      {extra_sql}
    ORDER BY (e.validade::date) ASC, (COALESCE(e.saldo, 0) * COALESCE(e.valor_unitario, 0)) DESC
    """
        try:
            return execute_query(session, sql, params)
        except Exception:
            session.rollback()
    return []


def get_predictive_raw(
    session: Session,
    sector: Optional[str] = None,
    warehouse: Optional[str] = None,
    material_group: Optional[str] = None,
    material_search: Optional[str] = None,
) -> tuple[List[dict], dict[str, float], dict[str, dict], dict[str, float]]:
    """
    Dados brutos para a análise preditiva: estoque por lote, consumo e último consumo.

    Consulta v_df_estoque (saldo > 0, validade na janela de 180 dias). A coluna MATERIAL da tabela
    exibe v_df_estoque.nome_do_material_padronizado (prioridade) ou nome_do_material (fallback).
    Retorna: (lista de lotes; mapa material_code -> soma 6 meses; mapa last_consumption; mapa material_code -> média
    últimos 6 meses). Cálculos de risco e perda ficam no serviço.
    """
    s_stock = schema_prefix(STOCK_VIEW)
    wh_clause, wh_params = _warehouse_clause(sector, warehouse)
    today = business_today()
    expiry_end = today + timedelta(days=EXPIRY_WINDOW_DAYS)
    params: dict[str, Any] = {
        "today": today,
        "expiry_end": expiry_end,
        **wh_params,
    }
    extra_stock_base: List[str] = []
    if material_group:
        extra_stock_base.append(" AND COALESCE(TRIM(e.grupo_de_material), 'Sem grupo') = :material_group")
        params["material_group"] = str(material_group).strip()
    if material_search:
        params["mat_search"] = f"%{material_search}%"

    # Relacionamento estoque × movimento: nome_do_material (estoque) = mat_cod_antigo (movimento); código = parte antes do '-'.
    # Tenta nome_do_material primeiro; fallback para nome_do_material_padronizado se a view não tiver a coluna.
    lote_expr = _stock_select_lote()
    stock_rows = _run_stock_query(
        session, s_stock, wh_clause, extra_stock_base, lote_expr, params, material_search
    )

    # Consumo: mesma lógica da tela TESTE (média últimos 6 meses por material; mês atual não entra).
    # Reutiliza get_teste_media_6m (view v_df_movimento ou fallback df_movimento).
    # consumption_6m = media_ultimos_6_meses * 6 (total no período) para avg_daily nas fórmulas de risco.
    # avg_monthly_map = material_code -> media_ultimos_6_meses (mesma regra: soma / meses com consumo > 0) para a coluna "Consumo médio/mês".
    teste_rows = get_teste_media_6m(session)
    consumption_map: dict[str, float] = {}
    avg_monthly_map: dict[str, float] = {}
    for r in teste_rows:
        mat = (r.get("material") or r.get("MATERIAL") or "").strip()
        if not mat:
            continue
        code = mat.split("-", 1)[0].strip() if "-" in mat else mat
        if not code:
            continue
        media = float(r.get("media_ultimos_6_meses") or r.get("MEDIA_ULTIMOS_6_MESES") or 0)
        consumption_map[code] = media * 6.0  # total nos 6 meses (para avg_daily = consumption_6m / dias)
        avg_monthly_map[code] = media  # mesma média da coluna "Média últimos 6 meses" (HISTÓRICO 6 MESES)
    total_consumption = sum(consumption_map.values())

    stock_codes = {str(r.get("material_code") or "").strip() for r in stock_rows}
    matched = sum(1 for c in stock_codes if consumption_map.get(c, 0) > 0)
    logger.info(
        "predictive_consumption_diagnostic",
        teste_consumption_rows=len(teste_rows),
        consumption_total=total_consumption,
        consumption_map_size=len(consumption_map),
        stock_rows=len(stock_rows),
        stock_codes_sample=list(stock_codes)[:5] if stock_codes else [],
        consumption_keys_sample=list(consumption_map.keys())[:5] if consumption_map else [],
        materials_with_consumption=matched,
    )

    last_consumption_map = get_last_consumption_by_material(session)
    today = business_today()
    # Enriquecer média para materiais com último consumo no período 6m mas ausentes na agregação
    # (ex.: get_teste_media_6m filtra por almoxarifados; último consumo não filtra — evita "média 0" com "último consumo" preenchido)
    for code, info in last_consumption_map.items():
        if not code or not isinstance(info, dict):
            continue
        if avg_monthly_map.get(code, 0.0) != 0.0:
            continue
        last_mesano = info.get("last_mesano")
        qtde = info.get("qtde_ultimo_consumo")
        if qtde is None or (isinstance(qtde, (int, float)) and float(qtde) <= 0):
            continue
        if not _last_mesano_in_6m_window(last_mesano, today):
            continue
        q = float(qtde)
        avg_monthly_map[code] = q  # média = consumo naquele mês (1 mesano no período)
        consumption_map[code] = q  # total no período = esse mês (para avg_daily consistente)
    total_consumption = sum(consumption_map.values())
    return stock_rows, consumption_map, last_consumption_map, avg_monthly_map
