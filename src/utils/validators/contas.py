from typing import Final

from flask import abort

from .validators import parse_boolish, require_fields


_TIPOS_CONTA_RECORRENTE: Final[set[str]] = {
    # moradia / comida / beleza
    "aluguel", "luz", "agua", "internet", "gas",
    # rodas
    "ipva", "seguro_veiculo", "financiamento_veiculo", "garagem",
    # transporte / mãos à obra
    "transporte", "combustivel", "equipamentos",
    # digital / freelancer / representação
    "ferramentas", "assinaturas", "celular",
    # genérico
    "boleto", "outros",
}


def validate_conta_recorrente_payload(body: dict) -> dict:
    """Valida o corpo da requisicao de upsert de conta recorrente."""
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

    lembrete_ativo = parse_boolish(body.get("lembrete_ativo", False), "lembrete_ativo")

    body["tipo"] = tipo
    body["dia_vencimento"] = dia_vencimento
    body["lembrete_ativo"] = lembrete_ativo

    return body


def validate_patch_conta_payload(body: dict) -> dict:
    """Valida o corpo de uma requisição PATCH de conta recorrente.

    Campos patcháveis: descricao, valor, dia_vencimento, lembrete_ativo, ativo
    Retorna apenas os campos presentes (ignora extras).
    Aborta 400 se nenhum campo patchável for fornecido.
    """
    _PATCHABLE = {"descricao", "valor", "dia_vencimento", "lembrete_ativo", "ativo"}

    result = {}

    if "descricao" in body:
        result["descricao"] = str(body["descricao"]).strip()

    if "valor" in body:
        try:
            result["valor"] = float(body["valor"])
        except (TypeError, ValueError):
            abort(400, description="o campo 'valor' deve ser um número")

    if "dia_vencimento" in body:
        try:
            dia_vencimento = int(body["dia_vencimento"])
        except (TypeError, ValueError):
            abort(400, description="o campo 'dia_vencimento' deve ser inteiro entre 1 e 31")

        if dia_vencimento < 1 or dia_vencimento > 31:
            abort(400, description="o campo 'dia_vencimento' deve ser inteiro entre 1 e 31")

        result["dia_vencimento"] = dia_vencimento

    if "lembrete_ativo" in body:
        result["lembrete_ativo"] = parse_boolish(body["lembrete_ativo"], "lembrete_ativo")

    if "ativo" in body:
        result["ativo"] = parse_boolish(body["ativo"], "ativo")

    if not result:
        abort(400, description="nenhum campo patchável fornecido")

    return result
