from typing import Final

from flask import abort

from .validators import parse_boolish, require_fields


_TIPOS_CONTA_RECORRENTE: Final[set[str]] = {
    "aluguel",
    "internet",
    "luz",
    "agua",
    "boleto",
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
