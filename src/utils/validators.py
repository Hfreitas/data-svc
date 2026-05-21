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


_SCOPE_AGENDAMENTO_ALIASES: Final[dict[str, str]] = {
    "future": "future"
}

_STATUS_AGENDAMENTO: Final[set[str]] = {
    "pendente",
    "confirmado",
    "agendado",
    "cancelado"
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


def validate_scope_agendamento(scope: str) -> str:
    """Valida se o escopo informado em agendamentos é correto"""
    raw = (scope or "").strip().lower()
    normalizado = _SCOPE_AGENDAMENTO_ALIASES.get(raw)

    if normalizado is None:
        permitidos = ", ".join(sorted(_SCOPE_AGENDAMENTO_ALIASES.keys()))
        abort(400, description=f"parâmetro 'scope' inválido. Use: {permitidos}")

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


def validate_update_agendamento_payload(body: dict) -> dict:
    """Valida o corpo da requisição de atualização de um agendamento
    
    Aceita campos opcionais: nome_compromisso, data_compromisso, hora_compromisso, status
    Pelo menos um campo deve ser fornecido.
    """
    if not body:
        abort(400, description="body não pode estar vazio")
    
    campos_validos = {"nome_compromisso", "data_compromisso", "hora_compromisso", "status"}
    campos_fornecidos = set(body.keys())
    
    if not campos_fornecidos.intersection(campos_validos):
        abort(400, description=f"pelo menos um campo deve ser fornecido: {', '.join(sorted(campos_validos))}")
    
    resultado = {}
    tz = ZoneInfo("America/Sao_Paulo")
    
    # Validar e processar nome_compromisso
    if "nome_compromisso" in body:
        nome_compromisso = str(body.get("nome_compromisso", "")).strip()
        if nome_compromisso and nome_compromisso != body.get("nome_compromisso"):
            abort(400, description="o campo 'nome_compromisso' não deve ser vazio ou apenas espaços")
        if nome_compromisso:
            resultado["nome_compromisso"] = nome_compromisso
    
    # Validar e processar data_compromisso
    if "data_compromisso" in body:
        try:
            data_compromisso = date.fromisoformat(str(body.get("data_compromisso", "")).strip())
        except (TypeError, ValueError):
            abort(400, description="o campo 'data_compromisso' deve estar no formato YYYY-MM-DD")
        
        agora = datetime.now(tz)
        hoje = agora.date()
        
        if data_compromisso < hoje:
            abort(400, description="não é permitido agendar uma data no passado")
        
        resultado["data_compromisso"] = data_compromisso.isoformat()
    
    # Validar e processar hora_compromisso
    if "hora_compromisso" in body:
        try:
            hora_compromisso = datetime.strptime(str(body.get("hora_compromisso", "")).strip(), "%H:%M").time()
        except (TypeError, ValueError):
            abort(400, description="o campo 'hora_compromisso' deve estar no formato HH:MM")
        if "data_compromisso" in resultado:
            agora = datetime.now(tz)
            nova_data = date.fromisoformat(resultado["data_compromisso"])
            if nova_data == agora.date() and hora_compromisso <= agora.time():
                abort(400, description="não é permitido agendar um horário no passado")
        
        resultado["hora_compromisso"] = hora_compromisso.strftime("%H:%M")
    
    # Validar e processar status
    if "status" in body:
        status = str(body.get("status", "")).strip().lower()
        validate_status_agendamento(status)
        resultado["status"] = status
    
    return resultado

def validate_conflict_check_params(data: str, hora: str, nome_compromisso: str) -> tuple[date, str, str]:
    """Valida os query params para verificação de conflito de agendamento."""
    # Validar se os parâmetros foram fornecidos
    if not all([data, hora, nome_compromisso]):
        abort(400, description="Parâmetros 'data', 'hora' e 'nome_compromisso' são obrigatórios")
    
    tz = ZoneInfo("America/Sao_Paulo")

    # Validar data
    try:
        data_obj = date.fromisoformat(data.strip())
    except (TypeError, ValueError, AttributeError):
        abort(400, description="parâmetro 'data' deve estar no formato YYYY-MM-DD")

    agora = datetime.now(tz)
    hoje = agora.date()

    if data_obj < hoje:
        abort(400, description="não é permitido verificar conflito para data no passado")

    # Validar hora
    try:
        hora_obj = datetime.strptime(hora.strip(), "%H:%M").time()
    except (TypeError, ValueError, AttributeError):
        abort(400, description="parâmetro 'hora' deve estar no formato HH:MM")

    if data_obj == hoje and hora_obj <= agora.time():
        abort(400, description="não é permitido verificar conflito para horário no passado")

    # Validar nome_compromisso
    nome_compromisso_str = str(nome_compromisso or "").strip()
    if not nome_compromisso_str:
        abort(400, description="parâmetro 'nome_compromisso' não pode estar vazio")

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

    body["nome_compromisso"] = nome_compromisso
    body["data_inicio"] = data_inicio
    body["hora_compromisso"] = hora_compromisso.strftime("%H:%M")
    body["frequencia"] = frequencia
    body["dia_semana_ou_mes"] = dia_semana_ou_mes
    body["quantidade_meses"] = quantidade_meses

    return body


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


def validate_lista_delete_itens_payload(body: dict) -> list[str]:
    """Valida payload de remoção de itens e normaliza nomes para busca."""
    nomes = body.get("nomes")
    if not isinstance(nomes, list) or not nomes:
        abort(400, description="o campo 'nomes' deve ser um array com pelo menos um item")

    nomes_normalizados: list[str] = []
    for idx, nome in enumerate(nomes):
        nome_normalizado = str(nome).strip().lower()
        if not nome_normalizado:
            abort(400, description=f"o item na posição {idx} do campo 'nomes' não pode ser vazio")
        nomes_normalizados.append(nome_normalizado)

    return nomes_normalizados