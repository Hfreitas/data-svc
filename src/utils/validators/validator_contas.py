from typing import Final

from flask import abort
from src.utils.validators.validator import require_fields


_TIPOS_CONTA_RECORRENTE: Final[set[str]] = {
    "aluguel",
    "internet",
    "luz",
    "agua",
    "boleto",
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
