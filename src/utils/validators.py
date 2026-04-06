from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
import stat
from typing import Final
from zoneinfo import ZoneInfo
from flask import abort


_MODO_ALIASES: Final[dict[str, str]] = {
    "gastos": "gasto",
    "vendas": "venda",
    "gasto": "gasto",
    "venda": "venda",
    "relatorio": "relatorio",
}

_OPERACAO_ALIASES: Final[dict[str, str]] = {
    "gastos": "gasto",
    "vendas": "venda",
    "gasto": "gasto",
    "venda": "venda",
}

_SEMANA_ALIASES: Final[dict[str, str]] = {
    "atual": "atual"
}

_STATUS_AGENDAMENTO: Final[set[str]] = {
    "pendente",
    "confirmado",
    "agendado"
}


def require_fields(body: dict, *fields: str):
    """Aborta com 400 se algum campo obrigatório estiver ausente."""
    missing = [f for f in fields if f not in body or body[f] is None]
    if missing:
        abort(400, description=f"campos obrigatórios ausentes: {', '.join(missing)}")


def validate_mes(mes: str) -> str:
    """Valida e retorna o parâmetro ?mes=YYYY-MM."""
    if not mes or not re.match(r"^\d{4}-\d{2}$", mes):
        abort(400, description="parâmetro 'mes' deve estar no formato YYYY-MM")
    return mes


def validate_telefone(telefone: str) -> str:
    """Valida número de telefone (somente dígitos, 10-13 chars)."""
    if not telefone or not re.match(r"^\d{10,13}$", telefone):
        abort(400, description="parâmetro 'telefone' inválido")
    return telefone


def validate_modo(modo: str) -> str:
    """Valida o modo de um comprovante em relatorio | gastos | vendas"""
    raw = (modo or "").strip().lower()
    normalizado = _MODO_ALIASES.get(raw)

    if normalizado is None:
        permitidos = ", ".join(sorted(_MODO_ALIASES.keys()))
        abort(400, description=f"parâmetro 'modo' inválido. Use: {permitidos}")

    return normalizado


def validate_comprovante_payload(body: dict) -> dict:
    """Valida o corpo da requisição do upsert de um comprovante"""
    operacao_raw = str(body.get("operacao", "")).strip().lower()
    operacao = _OPERACAO_ALIASES.get(operacao_raw)
    if operacao not in _OPERACAO_ALIASES:
        permitidos = ", ".join(sorted(_OPERACAO_ALIASES.keys()))
        abort(400, description=f"o campo 'operacao' está inválido. Use: {permitidos}")
        
    item = str(body.get("item", "")).strip()
    if not item:
        abort(400, description="o campo 'item' não pode ser vazio")

    item_hash = str(body.get("item_hash", "")).strip()
    if not item_hash:
        abort(400, description="o campo 'item_hash' não pode ser vazio")
    
    try:
        qtd = Decimal(str(body.get("quantidade")))
        vu = Decimal(str(body.get("valor_unitario")))
        vt = Decimal(str(body.get("valor_total")))
    except (InvalidOperation, TypeError):
        abort(400, description="quantidade, valor_unitario e valor_total devem ser numéricos")

    if qtd <= 0 or vu < 0 or vt < 0:
        abort(400, description="o campo 'quantidade' deve ser > 0 e os valores >= 0")
     
    data_venda = None   
    data_compra = None    
    if operacao == "venda":
        data_venda = body.get("data_venda")
    else:
        data_compra = body.get("data_compra")

    if operacao == "venda" and not data_venda:
        abort(400, description="o campo 'data_venda' é obrigatório para operacao='venda'")
    if operacao == "gasto" and not data_compra:
        abort(400, description="o campo 'data_compra' é obrigatório para operacao='gasto'")

    body["operacao"] = operacao
    body["item"] = item
    body["item_hash"] = item_hash
    return body


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
    
    if not body.get("nome_compromisso").strip():
        return abort(400, description="o campo 'nome_compromisso' não deve ser vazio")
    
    tz = ZoneInfo("America/Sao_Paulo")

    try:
        data_compromisso = date.fromisoformat(body.get("data_compromisso"))
    except (TypeError, ValueError):
        return abort(400, description="o campo 'data_compromisso' deve estar no formato YYYY-MM-DD")
    
    try:
        hora_compromisso = datetime.strptime(body.get("hora_compromisso"), "%H:%M").time()
    except ValueError:
        return abort(400, "o campo 'hora_compromisso' deve estar no formato HH:MM")

    agora = datetime.now(tz)
    hoje = agora.date()

    if data_compromisso < hoje:
        return abort(400, "não é permitido agendar uma data no passado")

    if data_compromisso == hoje and hora_compromisso <= agora.time():
        return abort(400, "não é permitido agendar um horário no passado")
    
    return body


def validade_status_agendamento(status: str) -> str:
    """Valida se o status informado para o agendamento é correto"""
    if not status:
        return abort(400, description="o campo 'status' não pode ser vazio")
    
    status = status.lower()
    
    if status not in _STATUS_AGENDAMENTO:
        permitidos = ", ".join(sorted(_STATUS_AGENDAMENTO))
        abort(400, description=f"o campo 'status' está inválido. Use: {permitidos}")
        
    return status       