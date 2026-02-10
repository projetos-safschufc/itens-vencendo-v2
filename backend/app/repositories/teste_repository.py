"""
Repositório: aba TESTE – média dos últimos 6 meses por material.
Fonte: v_df_movimento ou df_movimento.
v_df_movimento pode ter uma de duas estruturas:
  - Estilo view: mat_cod_antigo, data_movimento, quantidade, movimento_cd/movimento_subtipo, almoxarifado
  - Estilo tabela: mat_cod_antigo, mesano, qtde_orig, movimento_cd/movimento_subtipo, alm_nome (mesma da df_movimento)
Fallback: df_movimento (mat_cod_antigo, mesano, qtde_orig, alm_nome).
Coluna de referência para material: mat_cod_antigo (formato código-descrição). Usada para agrupamento e exibição.
Critérios: movimento tipo RM, quantidade/qtde_orig > 0, período >= 2023-01 (sem filtro por almoxarifado; alinhado à Análise Preditiva).
Últimos 6 meses: do (mês atual - 1) retrocedendo 6 meses pela coluna mesano (mês atual NÃO entra).
Média: SUM(qtde_orig) / COUNT(DISTINCT mesano) no período filtrado (movimento_cd = RM, qtde_orig > 0).
Filtro opcional: código/material (ILIKE em mat_cod_antigo e na parte antes do '-').
"""
from typing import Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.repositories.base import execute_query, schema_prefix

logger = get_logger(__name__)

MOV_VIEW = "v_df_movimento"
MOV_TABLE = "df_movimento"

# Coluna de referência para material em v_df_movimento e df_movimento (formato código-descrição). Usada no GROUP BY e na exibição.
MATERIAL_REF_COLUMN = "mat_cod_antigo"

# Filtro de movimento para consumo (RM). Na view usa movimento_subtipo; na tabela pode ser movimento_cd.
MOVIMENTO_CONSUMO = "RM"


# Cláusula WHERE opcional para filtro por código/material (coluna de referência ou parte antes do '-').
MATERIAL_FILTER_WHERE = f" AND (m.{MATERIAL_REF_COLUMN} ILIKE :mat OR SPLIT_PART(m.{MATERIAL_REF_COLUMN}::text, '-', 1) ILIKE :mat)"


def _filter_empty_material_rows(rows: List[dict]) -> List[dict]:
    """Remove linhas em que material (ou MATERIAL) está vazio/nulo (ex.: agrupamento por mat_cod_antigo nulo)."""
    return [
        r for r in rows
        if (str(r.get("material") or r.get("MATERIAL") or "").strip())
    ]


def _last_6m_view_sql(mov: str, material_where: str = "") -> str:
    """
    Monta a SQL para média de consumo dos últimos 6 meses usando a view v_df_movimento.

    Coluna de referência para material: mat_cod_antigo (MATERIAL_REF_COLUMN).
    Colunas da view: mat_cod_antigo, data_movimento, quantidade, almoxarifado.

    Regra da média: Média = SUM(quantidade) / COUNT(DISTINCT mes/ano) no período (mês atual excluído; movimento RM; quantidade > 0).
    Período: do (mês atual - 1) retrocedendo 6 meses (mês atual não entra).
    """
    ref = MATERIAL_REF_COLUMN
    return f"""
    SELECT
      sub.material,
      COALESCE(
        (sub.total / NULLIF(sub.meses_com_consumo::float, 0))::float,
        0
      ) AS media_ultimos_6_meses
    FROM (
      SELECT
        MAX(m.{ref}::text) AS material,
        SUM(COALESCE(m.quantidade, 0)) AS total,
        COUNT(DISTINCT date_trunc('month', m.data_movimento))::int AS meses_com_consumo
      FROM {mov} m
      WHERE COALESCE(m.movimento_cd, m.movimento_subtipo, '') = :movimento_consumo
        AND COALESCE(m.quantidade, 0) > 0
        AND m.data_movimento >= '2023-01-01'
        AND m.data_movimento >= (date_trunc('month', CURRENT_DATE) - INTERVAL '6 months')::date
        AND m.data_movimento < date_trunc('month', CURRENT_DATE)::date
        {material_where}
      GROUP BY TRIM(SPLIT_PART(m.{ref}::text, '-', 1))
    ) sub
    ORDER BY media_ultimos_6_meses DESC
    """


def _last_6m_table_sql(
    tbl: str, mesano_as_date: bool, material_where: str = "", use_almoxarifado: bool = False
) -> str:
    """
    Query usando tabela/view com mesano (date ou int YYYYMM), qtde_orig; alm_nome ou almoxarifado conforme use_almoxarifado.
    Regra da média: Média = SUM(qtde_orig) / COUNT(DISTINCT mesano) no período (mês atual excluído; movimento_cd RM; qtde_orig > 0).
    """
    if mesano_as_date:
        mesano_cond = """
      AND (m.mesano::date) >= '2023-01-01'
      AND (m.mesano::date) >= (date_trunc('month', CURRENT_DATE) - INTERVAL '6 months')::date
      AND (m.mesano::date) < date_trunc('month', CURRENT_DATE)::date"""
        count_meses = "COUNT(DISTINCT date_trunc('month', m.mesano::date))::int"
    else:
        mesano_cond = """
      AND m.mesano >= 202301
      AND m.mesano >= (EXTRACT(YEAR FROM (date_trunc('month', CURRENT_DATE) - INTERVAL '6 months'))::int * 100
           + EXTRACT(MONTH FROM (date_trunc('month', CURRENT_DATE) - INTERVAL '6 months'))::int)
      AND m.mesano < (EXTRACT(YEAR FROM CURRENT_DATE)::int * 100 + EXTRACT(MONTH FROM CURRENT_DATE)::int)"""
        count_meses = "COUNT(DISTINCT m.mesano)::int"
    ref = MATERIAL_REF_COLUMN
    mov_cond = "COALESCE(m.movimento_cd, m.movimento_subtipo, '') = :movimento_consumo"
    return f"""
    SELECT
      sub.material,
      COALESCE(
        (sub.total / NULLIF(sub.meses_com_consumo::float, 0))::float,
        0
      ) AS media_ultimos_6_meses
    FROM (
      SELECT
        MAX(m.{ref}::text) AS material,
        SUM(COALESCE(m.qtde_orig, 0)) AS total,
        {count_meses} AS meses_com_consumo
      FROM {tbl} m
      WHERE {mov_cond}
        AND COALESCE(m.qtde_orig, 0) > 0
        {mesano_cond}
        {material_where}
      GROUP BY TRIM(SPLIT_PART(m.{ref}::text, '-', 1))
    ) sub
    ORDER BY media_ultimos_6_meses DESC
    """


def _seven_months_ref() -> List[Tuple[int, int]]:
    """Retorna 7 (ano, mês) do M-6 ao Mês Atual (índice 0 = M-6, 6 = Mês Atual)."""
    from datetime import date
    today = date.today()
    y, m = today.year, today.month
    out: List[Tuple[int, int]] = []
    for i in range(6, -1, -1):
        # i meses atrás: subtrair i meses
        total_months = (y * 12 + m) - i
        ym = total_months // 12
        mm = total_months % 12
        if mm <= 0:
            mm += 12
            ym -= 1
        out.append((ym, mm))
    return out


def _consumo_por_mesano_view_sql(mov: str, material_where: str, mesano_dates: List[Any]) -> str:
    """SQL consumo por mesano usando view com data_movimento (7 meses)."""
    ref = MATERIAL_REF_COLUMN
    # mesano_dates: lista de 7 dates (primeiro dia de cada mês)
    placeholders = ", ".join(f":d{i}" for i in range(7))
    return f"""
    SELECT
      MAX(m.{ref}::text) AS material,
      TRIM(SPLIT_PART(m.{ref}::text, '-', 1)) AS material_code,
      (date_trunc('month', m.data_movimento))::date AS mesano_date,
      SUM(COALESCE(m.quantidade, 0)) AS consumo
    FROM {mov} m
    WHERE COALESCE(m.movimento_cd, m.movimento_subtipo, '') = :movimento_consumo
      AND COALESCE(m.quantidade, 0) > 0
      AND m.data_movimento >= '2023-01-01'
      AND (date_trunc('month', m.data_movimento))::date IN ({placeholders})
      {material_where}
    GROUP BY TRIM(SPLIT_PART(m.{ref}::text, '-', 1)), date_trunc('month', m.data_movimento)
    """


def _consumo_por_mesano_table_sql(
    tbl: str, material_where: str, mesano_ints: List[int], use_almoxarifado: bool = False
) -> str:
    """SQL consumo por mesano: mesano int YYYYMM (sem filtro por almoxarifado)."""
    ref = MATERIAL_REF_COLUMN
    placeholders = ", ".join(f":m{i}" for i in range(7))
    mov_cond = "COALESCE(m.movimento_cd, m.movimento_subtipo, '') = :movimento_consumo"
    return f"""
    SELECT
      MAX(m.{ref}::text) AS material,
      TRIM(SPLIT_PART(m.{ref}::text, '-', 1)) AS material_code,
      m.mesano AS mesano_int,
      SUM(COALESCE(m.qtde_orig, 0)) AS consumo
    FROM {tbl} m
    WHERE {mov_cond}
      AND COALESCE(m.qtde_orig, 0) > 0
      AND m.mesano IN ({placeholders})
      {material_where}
    GROUP BY TRIM(SPLIT_PART(m.{ref}::text, '-', 1)), m.mesano
    """


def _consumo_por_mesano_table_sql_mesano_date(
    tbl: str, material_where: str, mesano_ints: List[int], use_almoxarifado: bool = False
) -> str:
    """SQL consumo por mesano quando mesano é date/timestamp (sem filtro por almoxarifado)."""
    ref = MATERIAL_REF_COLUMN
    placeholders = ", ".join(f":m{i}" for i in range(7))
    mov_cond = "COALESCE(m.movimento_cd, m.movimento_subtipo, '') = :movimento_consumo"
    yyyyymm_expr = "(EXTRACT(YEAR FROM m.mesano::date)::int * 100 + EXTRACT(MONTH FROM m.mesano::date)::int)"
    return f"""
    SELECT
      MAX(m.{ref}::text) AS material,
      TRIM(SPLIT_PART(m.{ref}::text, '-', 1)) AS material_code,
      {yyyyymm_expr} AS mesano_int,
      SUM(COALESCE(m.qtde_orig, 0)) AS consumo
    FROM {tbl} m
    WHERE {mov_cond}
      AND COALESCE(m.qtde_orig, 0) > 0
      AND {yyyyymm_expr} IN ({placeholders})
      {material_where}
    GROUP BY TRIM(SPLIT_PART(m.{ref}::text, '-', 1)), {yyyyymm_expr}
    """


def get_teste_consumo_por_mesano(
    session: Session,
    material: Optional[str] = None,
    month_refs: Optional[List[Tuple[int, int]]] = None,
) -> List[dict]:
    """
    Retorna consumo por (material, mesano) para 7 meses (M-6 até Mês Atual).
    Cada item: {material, material_code, mesano_yyyymm, consumo}.
    mesano_yyyymm = int YYYYMM para alinhar com month_refs.
    month_refs: lista de 7 (ano, mês); se None, usa _seven_months_ref().
    """
    if month_refs is None:
        month_refs = _seven_months_ref()
    if len(month_refs) != 7:
        return []
    params: dict[str, Any] = {"movimento_consumo": MOVIMENTO_CONSUMO}
    material_where = ""
    if material is not None and str(material).strip():
        params["mat"] = f"%{material.strip()}%"
        material_where = MATERIAL_FILTER_WHERE

    # mesano como int YYYYMM para cada um dos 7 meses
    mesano_ints = [y * 100 + m for y, m in month_refs]
    for i, v in enumerate(mesano_ints):
        params[f"m{i}"] = v

    mov = schema_prefix(MOV_VIEW)
    tbl = schema_prefix(MOV_TABLE)

    out: List[dict] = []

    def _append_rows(rows: List[dict]) -> None:
        for r in rows:
            mat = (r.get("material") or "").strip()
            code = (r.get("material_code") or "").strip()
            mi = r.get("mesano_int")
            consumo = float(r.get("consumo") or 0)
            if not code:
                continue
            try:
                yyyyymm = int(mi) if mi is not None else None
            except (TypeError, ValueError):
                continue
            if yyyyymm is not None:
                out.append({"material": mat, "material_code": code, "mesano_yyyymm": yyyyymm, "consumo": consumo})

    # 1) View/tabela com mesano (estilo tabela): mesano date ou int — alinhado a get_teste_media_6m (evita data_movimento inexistente)
    for source, name in [(mov, "view"), (tbl, "table")]:
        for use_alm in [False, True]:
            try:
                sql = _consumo_por_mesano_table_sql_mesano_date(
                    source, material_where, mesano_ints, use_almoxarifado=use_alm
                )
                rows = execute_query(session, sql, params)
                _append_rows(rows)
                if out:
                    return out
            except Exception as e:
                logger.warning(
                    f"teste_consumo_por_mesano {name} (mesano date, almoxarifado={use_alm}) failed", error=str(e)
                )
                session.rollback()

    for source, name in [(mov, "view"), (tbl, "table")]:
        try:
            sql = _consumo_por_mesano_table_sql(source, material_where, mesano_ints, use_almoxarifado=False)
            rows = execute_query(session, sql, params)
            _append_rows(rows)
            if out:
                return out
        except Exception as e:
            logger.warning(f"teste_consumo_por_mesano {name} (mesano int, alm_nome) failed", error=str(e))
            session.rollback()

    for source, name in [(mov, "view"), (tbl, "table")]:
        try:
            sql = _consumo_por_mesano_table_sql(source, material_where, mesano_ints, use_almoxarifado=True)
            rows = execute_query(session, sql, params)
            _append_rows(rows)
            if out:
                return out
        except Exception as e:
            logger.warning(f"teste_consumo_por_mesano {name} (mesano int, almoxarifado) failed", error=str(e))
            session.rollback()

    # 2) Por último: view com data_movimento/quantidade (estilo view), se a base tiver essa estrutura
    from datetime import date as date_type
    mesano_dates = [date_type(y, m, 1) for y, m in month_refs]
    for i, d in enumerate(mesano_dates):
        params[f"d{i}"] = d
    try:
        sql = _consumo_por_mesano_view_sql(mov, material_where, mesano_dates)
        rows = execute_query(session, sql, params)
        for r in rows:
            mat = (r.get("material") or "").strip()
            code = (r.get("material_code") or "").strip()
            dt = r.get("mesano_date")
            consumo = float(r.get("consumo") or 0)
            if not code:
                continue
            yyyyymm = None
            if hasattr(dt, "year") and hasattr(dt, "month"):
                yyyyymm = dt.year * 100 + dt.month
            elif isinstance(dt, str) and len(dt) >= 7:
                try:
                    yyyyymm = int(dt[:4]) * 100 + int(dt[5:7])
                except (ValueError, TypeError):
                    pass
            if yyyyymm is not None:
                out.append({"material": mat, "material_code": code, "mesano_yyyymm": yyyyymm, "consumo": consumo})
        if out:
            return out
    except Exception as e:
        logger.warning("teste_consumo_por_mesano view (data_movimento) failed", error=str(e))
        session.rollback()

    return out


def get_teste_media_6m(session: Session, material: Optional[str] = None) -> List[dict]:
    """
    Retorna lista de {mat_cod_antigo, media_ultimos_6_meses}.
    material: filtro opcional por código/descrição (ILIKE em mat_cod_antigo e na parte antes do '-').
    Ordem de tentativas: (1) v_df_movimento com colunas estilo-view (data_movimento, quantidade, almoxarifado);
    (2) v_df_movimento com colunas estilo-tabela (mesano, qtde_orig, alm_nome) quando a view tiver essa estrutura;
    (3) tabela df_movimento (mesano, qtde_orig, alm_nome).
    Critérios em todos: movimento RM, quantidade > 0, período >= 2023-01 (sem filtro por almoxarifado); mês atual não entra.
    """
    params: dict[str, Any] = {"movimento_consumo": MOVIMENTO_CONSUMO}
    material_where = ""
    if material is not None and str(material).strip():
        params["mat"] = f"%{material.strip()}%"
        material_where = MATERIAL_FILTER_WHERE

    mov = schema_prefix(MOV_VIEW)
    tbl = schema_prefix(MOV_TABLE)

    # 1) View v_df_movimento com colunas estilo-tabela (mesano, qtde_orig)
    for use_mesano_date in (True, False):
        try:
            sql = _last_6m_table_sql(
                mov,
                mesano_as_date=use_mesano_date,
                material_where=material_where,
                use_almoxarifado=False,
            )
            rows = execute_query(session, sql, params)
            if rows:
                return _filter_empty_material_rows(rows)
        except Exception as e:
            logger.warning(
                "teste_repository view (table-style columns) failed",
                mesano_as_date=use_mesano_date,
                error=str(e),
                exc_info=True,
            )
            session.rollback()

    # 2) View v_df_movimento com colunas estilo-view (data_movimento, quantidade, almoxarifado)
    try:
        sql = _last_6m_view_sql(mov, material_where=material_where)
        rows = execute_query(session, sql, params)
        if rows:
            return _filter_empty_material_rows(rows)
    except Exception as e:
        logger.warning(
            "teste_repository view (view-style columns) failed",
            error=str(e),
            exc_info=True,
        )
        session.rollback()

    # 3) Fallback: tabela df_movimento (mesano, qtde_orig, alm_nome)
    for use_mesano_date in (True, False):
        try:
            sql = _last_6m_table_sql(tbl, mesano_as_date=use_mesano_date, material_where=material_where)
            rows = execute_query(session, sql, params)
            if rows:
                return _filter_empty_material_rows(rows)
        except Exception as e:
            logger.warning(
                "teste_repository table failed",
                mesano_as_date=use_mesano_date,
                error=str(e),
                exc_info=True,
            )
            session.rollback()

    return []
