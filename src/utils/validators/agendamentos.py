from datetime import date, datetime
from typing import Final
from zoneinfo import ZoneInfo

from flask import abort

from .validators import (
    now_time_zone,
    normalize_non_empty_text,
    parse_hhmm_time,
    parse_iso_date,
    require_fields,
)


_SCOPE_AGENDAMENTO_ALIASES: Final[dict[str, str]] = {
    "future": "future",
}

_STATUS_AGENDAMENTO: Final[set[str]] = {
    "pendente",
    "confirmado",
    "agendado",
    "cancelado",
}


def validate_scope_agendamento(scope: str) -> str:
    """Valida se o escopo informado em agendamentos e correto."""
    raw = (scope or "").strip().lower()
    normalizado = _SCOPE_AGENDAMENTO_ALIASES.get(raw)

    if normalizado is None:
        permitidos = ", ".join(sorted(_SCOPE_AGENDAMENTO_ALIASES.keys()))
        abort(400, description=f"parâmetro 'scope' inválido. Use: {permitidos}")

    return normalizado


def validate_agendamento_payload(body: dict) -> dict:
    """Valida o corpo da requisicao de create de um agendamento."""
    require_fields(body, "nome_compromisso", "data_compromisso", "hora_compromisso")

    nome_compromisso = normalize_non_empty_text(
        body.get("nome_compromisso", ""),
        "nome_compromisso",
        "o campo 'nome_compromisso' não deve ser vazio",
    )

    data_compromisso = parse_iso_date(
        body.get("data_compromisso", ""),
        "data_compromisso",
        "o campo 'data_compromisso' deve estar no formato YYYY-MM-DD",
    )
    hora_compromisso = parse_hhmm_time(
        body.get("hora_compromisso", ""),
        "hora_compromisso",
        "o campo 'hora_compromisso' deve estar no formato HH:MM",
    )

    agora = now_time_zone()
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
    """Valida se o status informado para o agendamento e correto."""
    if not status:
        abort(400, description="o campo 'status' não pode ser vazio")

    status = status.lower()

    if status not in _STATUS_AGENDAMENTO:
        permitidos = ", ".join(sorted(_STATUS_AGENDAMENTO))
        abort(400, description=f"o campo 'status' está inválido. Use: {permitidos}")

    return status


def validate_update_agendamento_payload(body: dict) -> dict:
    """Valida o corpo da requisicao de atualizacao de um agendamento."""
    if not body:
        abort(400, description="body não pode estar vazio")

    campos_validos = {"nome_compromisso", "data_compromisso", "hora_compromisso", "status"}
    campos_fornecidos = set(body.keys())

    if not campos_fornecidos.intersection(campos_validos):
        abort(400, description=f"pelo menos um campo deve ser fornecido: {', '.join(sorted(campos_validos))}")

    resultado = {}

    if "nome_compromisso" in body:
        nome_compromisso = str(body.get("nome_compromisso", "")).strip()
        if nome_compromisso and nome_compromisso != body.get("nome_compromisso"):
            abort(400, description="o campo 'nome_compromisso' não deve ser vazio ou apenas espaços")
        if nome_compromisso:
            resultado["nome_compromisso"] = nome_compromisso

    if "data_compromisso" in body:
        data_compromisso = parse_iso_date(
            body.get("data_compromisso", ""),
            "data_compromisso",
            "o campo 'data_compromisso' deve estar no formato YYYY-MM-DD",
        )

        agora = now_time_zone()
        hoje = agora.date()
        if data_compromisso < hoje:
            abort(400, description="não é permitido agendar uma data no passado")

        resultado["data_compromisso"] = data_compromisso.isoformat()

    if "hora_compromisso" in body:
        hora_compromisso = parse_hhmm_time(
            body.get("hora_compromisso", ""),
            "hora_compromisso",
            "o campo 'hora_compromisso' deve estar no formato HH:MM",
        )
        if "data_compromisso" in resultado:
            agora = now_time_zone()
            nova_data = date.fromisoformat(resultado["data_compromisso"])
            if nova_data == agora.date() and hora_compromisso <= agora.time():
                abort(400, description="não é permitido agendar um horário no passado")

        resultado["hora_compromisso"] = hora_compromisso.strftime("%H:%M")

    if "status" in body:
        status = str(body.get("status", "")).strip().lower()
        validate_status_agendamento(status)
        resultado["status"] = status

    return resultado


def validate_conflict_check_params(data: str, hora: str, nome_compromisso: str) -> tuple[date, str, str]:
    """Valida os query params para verificacao de conflito de agendamento."""
    if not all([data, hora, nome_compromisso]):
        abort(400, description="Parâmetros 'data', 'hora' e 'nome_compromisso' são obrigatórios")

    data_obj = parse_iso_date(
        data,
        "data",
        "parâmetro 'data' deve estar no formato YYYY-MM-DD",
    )
    agora = now_time_zone()
    hoje = agora.date()

    if data_obj < hoje:
        abort(400, description="não é permitido verificar conflito para data no passado")

    hora_obj = parse_hhmm_time(
        hora,
        "hora",
        "parâmetro 'hora' deve estar no formato HH:MM",
    )

    if data_obj == hoje and hora_obj <= agora.time():
        abort(400, description="não é permitido verificar conflito para horário no passado")

    nome_compromisso_str = normalize_non_empty_text(
        nome_compromisso,
        "nome_compromisso",
        "parâmetro 'nome_compromisso' não pode estar vazio",
    )

    return data_obj, hora.strip(), nome_compromisso_str


def validate_recurrence_payload(body: dict) -> dict:
    """Valida o corpo da requisição de criação de agendamento recorrente."""
    require_fields(body, "nome_compromisso", "data_inicio", "hora_compromisso", "frequencia", "dia_semana_ou_mes", "quantidade_meses")

    nome_compromisso = str(body.get("nome_compromisso", "")).strip()
    if not nome_compromisso:
        abort(400, description="o campo 'nome_compromisso' não deve ser vazio")

    tz = ZoneInfo("America/Sao_Paulo")

    try:
        data_inicio = date.fromisoformat(str(body.get("data_inicio", "")).strip())
    except (TypeError, ValueError):
        abort(400, description="o campo 'data_inicio' deve estar no formato YYYY-MM-DD")

    try:
        hora_compromisso = datetime.strptime(str(body.get("hora_compromisso", "")).strip(), "%H:%M").time()
    except (TypeError, ValueError):
        abort(400, description="o campo 'hora_compromisso' deve estar no formato HH:MM")

    agora = datetime.now(tz)
    hoje = agora.date()

    if data_inicio < hoje:
        abort(400, description="o campo 'data_inicio' não pode estar no passado")

    if data_inicio == hoje and hora_compromisso <= agora.time():
        abort(400, description="não é permitido agendar um horário no passado")

    frequencia = str(body.get("frequencia", "")).strip().lower()
    if frequencia not in {"semanal", "quinzenal", "mensal"}:
        abort(400, description="o campo 'frequencia' deve ser 'semanal', 'quinzenal' ou 'mensal'")

    dia_semana_ou_mes = str(body.get("dia_semana_ou_mes", "")).strip().lower()
    if frequencia in {"semanal", "quinzenal"}:
        dias_validos = {"seg", "ter", "qua", "qui", "sex", "sab", "dom"}
        if dia_semana_ou_mes not in dias_validos:
            abort(400, description=f"para frequência '{frequencia}', 'dia_semana_ou_mes' deve ser um dia da semana: {', '.join(sorted(dias_validos))}")
    else:  # mensal
        try:
            dia_mes = int(dia_semana_ou_mes)
            if dia_mes < 1 or dia_mes > 31:
                abort(400, description="para frequência 'mensal', 'dia_semana_ou_mes' deve ser um número entre 1 e 31")
        except ValueError:
            abort(400, description="para frequência 'mensal', 'dia_semana_ou_mes' deve ser um número entre 1 e 31")

    try:
        quantidade_meses = int(body.get("quantidade_meses"))
    except (TypeError, ValueError):
        abort(400, description="o campo 'quantidade_meses' deve ser um inteiro")

    if quantidade_meses < 1 or quantidade_meses > 12:
        abort(400, description="o campo 'quantidade_meses' deve estar entre 1 e 12")

    return {
        "nome_compromisso": nome_compromisso,
        "data_inicio": data_inicio,
        "hora_compromisso": hora_compromisso.strftime("%H:%M"),
        "frequencia": frequencia,
        "dia_semana_ou_mes": dia_semana_ou_mes,
        "quantidade_meses": quantidade_meses,
    }
