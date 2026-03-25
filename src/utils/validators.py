import re
from flask import request, abort


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
