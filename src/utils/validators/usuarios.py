import re
from datetime import datetime

from flask import abort

from .validators import parse_boolish, normalize_non_empty_text


def validate_telefone(telefone: str) -> str:
    """Valida numero de telefone (somente digitos, 10-13 chars)."""
    if not telefone or not re.match(r"^\d{10,13}$", telefone):
        abort(400, description="parâmetro 'telefone' inválido")
    return telefone


def validate_usuario_agenda_fields(body: dict) -> dict:
    """Valida campos de agenda do usuário.

    Campos suportados:
    - contas_fixas_completo (bool)
    - onboarding_concluido (bool)
    - onboarding_timestamp (ISO datetime)
    - cluster (text não-vazio)

    Retorna dict com apenas os campos presentes e já normalizados.
    """
    result = {}

    if "contas_fixas_completo" in body:
        result["contas_fixas_completo"] = parse_boolish(
            body["contas_fixas_completo"], "contas_fixas_completo"
        )

    if "onboarding_concluido" in body:
        result["onboarding_concluido"] = parse_boolish(
            body["onboarding_concluido"], "onboarding_concluido"
        )

    if "onboarding_timestamp" in body:
        try:
            result["onboarding_timestamp"] = datetime.fromisoformat(
                str(body["onboarding_timestamp"]).strip()
            )
        except (TypeError, ValueError, AttributeError):
            abort(400, description="o campo 'onboarding_timestamp' deve estar no formato ISO")

    if "cluster" in body:
        result["cluster"] = normalize_non_empty_text(body["cluster"], "cluster")

    return result
