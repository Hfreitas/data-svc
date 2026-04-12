from datetime import date, datetime
from typing import Final
from zoneinfo import ZoneInfo

from flask import abort
from src.utils.validators.validator import require_fields


_SEMANA_ALIASES: Final[dict[str, str]] = {
    "atual": "atual"
}

_STATUS_AGENDAMENTO: Final[set[str]] = {
    "pendente",
    "confirmado",
    "agendado"
}


def validate_semana_agendamento(semana: str) -> str:
    """Valida se a semana informada em agendamentos é correta"""
    raw = (semana or "").strip().lower()
    normalizado = _SEMANA_ALIASES.get(raw)

    if normalizado is None:
        permitidos = ", ".join(sorted(_SEMANA_ALIASES.keys()))
        abort(400, description=f"parâmetro 'semana' inválido. Use: {permitidos}")

    return normalizado


def validate_agendamento_payload(body: dict) -> dict:
    """Valida o corpo da requisição de create de um agendamento"""
    require_fields(body, "nome_compromisso", "data_compromisso", "hora_compromisso")

    nome_compromisso = str(body.get("nome_compromisso", "")).strip()
    if not nome_compromisso:
        abort(400, description="o campo 'nome_compromisso' não deve ser vazio")

    tz = ZoneInfo("America/Sao_Paulo")

    try:
        data_compromisso = date.fromisoformat(str(body.get("data_compromisso", "")).strip())
    except (TypeError, ValueError):
        abort(400, description="o campo 'data_compromisso' deve estar no formato YYYY-MM-DD")

    try:
        hora_compromisso = datetime.strptime(str(body.get("hora_compromisso", "")).strip(), "%H:%M").time()
    except (TypeError, ValueError):
        abort(400, "o campo 'hora_compromisso' deve estar no formato HH:MM")

    agora = datetime.now(tz)
    hoje = agora.date()

    if data_compromisso < hoje:
        abort(400, "não é permitido agendar uma data no passado")

    if data_compromisso == hoje and hora_compromisso <= agora.time():
        abort(400, "não é permitido agendar um horário no passado")

    body["nome_compromisso"] = nome_compromisso
    body["data_compromisso"] = data_compromisso.isoformat()
    body["hora_compromisso"] = hora_compromisso.strftime("%H:%M")

    return body


def validate_status_agendamento(status: str) -> str:
    """Valida se o status informado para o agendamento é correto"""
    if not status:
        abort(400, description="o campo 'status' não pode ser vazio")

    status = status.lower()

    if status not in _STATUS_AGENDAMENTO:
        permitidos = ", ".join(sorted(_STATUS_AGENDAMENTO))
        abort(400, description=f"o campo 'status' está inválido. Use: {permitidos}")

    return status
