import re

from flask import abort
from src.utils.validators.validator import require_fields


def validate_telefone(telefone: str) -> str:
    """Valida número de telefone (somente dígitos, 10-13 chars)."""
    if not telefone or not re.match(r"^\d{10,13}$", telefone):
        abort(400, description="parâmetro 'telefone' inválido")
    return telefone
