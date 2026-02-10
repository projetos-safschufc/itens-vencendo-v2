"""
Data de negócio: "hoje" no fuso horário configurado (ex.: America/Sao_Paulo).
Evita disparidade entre data do servidor e data do usuário (ex.: Windows).
Use BUSINESS_DATE_OVERRIDE no .env (YYYY-MM-DD) para forçar a data quando o SO mostrar outra.
"""
from datetime import date, datetime

from zoneinfo import ZoneInfo

from app.config import get_settings


def business_today() -> date:
    """
    Retorna a data de hoje no fuso horário de negócio (BUSINESS_TIMEZONE).
    Se BUSINESS_DATE_OVERRIDE estiver definido (YYYY-MM-DD), retorna essa data.
    """
    settings = get_settings()
    override = (settings.business_date_override or "").strip()
    if override:
        try:
            return datetime.strptime(override, "%Y-%m-%d").date()
        except ValueError:
            pass
    tz_name = settings.business_timezone
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        return date.today()
    now = datetime.now(tz)
    return now.date()
