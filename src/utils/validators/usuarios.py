import re

from flask import abort


def validate_telefone(telefone: str) -> str:
    """Valida numero de telefone (somente digitos, 10-13 chars)."""
    if not telefone or not re.match(r"^\d{10,13}$", telefone):
        abort(400, description="parâmetro 'telefone' inválido")
    return telefone
