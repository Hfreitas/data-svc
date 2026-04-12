from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
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

_TIPOS_CONTA_RECORRENTE: Final[set[str]] = {
    "aluguel",
    "internet",
    "luz",
    "agua",
    "boleto",
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
    if operacao is None:
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
        data_venda = str(body.get("data_venda", "")).strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", data_venda):
            abort(400, description="o campo 'data_venda' deve estar no formato YYYY-MM-DD")
    else:
        data_compra = str(body.get("data_compra", "")).strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", data_compra):
            abort(400, description="o campo 'data_compra' deve estar no formato YYYY-MM-DD")

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


def validate_conta_recorrente_payload(body: dict) -> dict:
    """Valida o corpo da requisição de upsert de conta recorrente."""
    require_fields(body, "tipo", "descricao", "valor", "dia_vencimento")

    tipo = str(body.get("tipo", "")).strip().lower()
    if tipo not in _TIPOS_CONTA_RECORRENTE:
        permitidos = ", ".join(sorted(_TIPOS_CONTA_RECORRENTE))
        abort(400, description=f"o campo 'tipo' está inválido. Use: {permitidos}")

    try:
        dia_vencimento = int(body.get("dia_vencimento"))
    except (TypeError, ValueError):
        abort(400, description="o campo 'dia_vencimento' deve ser inteiro entre 1 e 31")

    if dia_vencimento < 1 or dia_vencimento > 31:
        abort(400, description="o campo 'dia_vencimento' deve ser inteiro entre 1 e 31")

    lembrete_ativo_raw = body.get("lembrete_ativo", False)
    if isinstance(lembrete_ativo_raw, bool):
        lembrete_ativo = lembrete_ativo_raw
    elif isinstance(lembrete_ativo_raw, str):
        valor = lembrete_ativo_raw.strip().lower()
        if valor in {"true", "1", "sim", "yes"}:
            lembrete_ativo = True
        elif valor in {"false", "0", "nao", "não", "no"}:
            lembrete_ativo = False
        else:
            abort(400, description="o campo 'lembrete_ativo' deve ser booleano")
    else:
        abort(400, description="o campo 'lembrete_ativo' deve ser booleano")

    body["tipo"] = tipo
    body["dia_vencimento"] = dia_vencimento
    body["lembrete_ativo"] = lembrete_ativo

    return body


def validate_lista_itens_payload(body: dict) -> list[dict]:
    """Valida payload de upsert de itens de lista e normaliza campos."""
    itens = body.get("itens")
    if not isinstance(itens, list) or not itens:
        abort(400, description="o campo 'itens' deve ser um array com pelo menos um item")

    itens_normalizados: list[dict] = []
    for idx, item in enumerate(itens):
        if not isinstance(item, dict):
            abort(400, description=f"o item na posição {idx} deve ser um objeto JSON")

        nome_item = str(item.get("nome_item", "")).strip()
        if not nome_item:
            abort(400, description=f"o campo 'nome_item' é obrigatório no item da posição {idx}")

        itens_normalizados.append(
            {
                "nome_item": nome_item,
                "quantidade": item.get("quantidade"),
                "preco_unitario": item.get("preco_unitario"),
            }
        )

    return itens_normalizados