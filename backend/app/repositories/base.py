"""
Utilitários para repositórios: execução de SQL com schema e tratamento de nulos.
"""
from typing import Any, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings


def _schema() -> str:
    return get_settings().db_schema


def _null_num(val: Any) -> float:
    """Converte nulo para 0 (regra de negócio)."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def execute_query(
    session: Session,
    sql: str,
    params: Optional[dict] = None,
) -> List[dict]:
    """Executa SQL e retorna lista de dicts; numéricos nulos como 0."""
    result = session.execute(text(sql), params or {})
    rows = result.mappings().fetchall()
    out = []
    for row in rows:
        d = dict(row)
        for k, v in d.items():
            if v is None and isinstance(k, str) and ("value" in k.lower() or "valor" in k.lower() or "quantity" in k.lower() or "saldo" in k.lower() or "quantidade" in k.lower()):
                d[k] = 0.0
        out.append(d)
    return out


def schema_prefix(table_or_view: str) -> str:
    """Retorna nome qualificado schema.tabela."""
    return f'"{_schema()}".{table_or_view}'
