from datetime import date, datetime, time

from flask import abort
from zoneinfo import ZoneInfo


TIME_ZONE = ZoneInfo("America/Sao_Paulo")


def require_fields(body: dict, *fields: str):
    """Aborta com 400 se algum campo obrigatório estiver ausente."""
    missing = [f for f in fields if f not in body or body[f] is None]
    if missing:
        abort(400, description=f"campos obrigatórios ausentes: {', '.join(missing)}")


def now_time_zone(time_zone: ZoneInfo | None = None) -> datetime:
    """Retorna datetime atual no fuso do Time Zone definido."""
    tz = time_zone or TIME_ZONE
    return datetime.now(tz)


def parse_iso_date(value: str, field_name: str, message: str | None = None) -> date:
    """Converte string para data ISO (YYYY-MM-DD) com erro de validação padronizado."""
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        abort(400, description=message or f"o campo '{field_name}' deve estar no formato YYYY-MM-DD")


def parse_hhmm_time(value: str, field_name: str, message: str | None = None) -> time:
    """Converte string para horário HH:MM com erro de validação padronizado."""
    try:
        return datetime.strptime(str(value).strip(), "%H:%M").time()
    except (TypeError, ValueError, AttributeError):
        abort(400, description=message or f"o campo '{field_name}' deve estar no formato HH:MM")


def normalize_non_empty_text(value: str, field_name: str, message: str | None = None) -> str:
    """Normaliza texto e garante que não seja vazio."""
    normalized = str(value or "").strip()
    if not normalized:
        abort(400, description=message or f"o campo '{field_name}' não pode ser vazio")
    return normalized


def parse_boolish(value, field_name: str) -> bool:
    """Converte booleano flexível (bool ou strings comuns) para bool."""
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "sim", "yes"}:
            return True
        if normalized in {"false", "0", "nao", "não", "no"}:
            return False

    abort(400, description=f"o campo '{field_name}' deve ser booleano")
