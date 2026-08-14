from decimal import Decimal, InvalidOperation
import re
from typing import Final

from flask import abort

from .validators import normalize_non_empty_text


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


def validate_mes(mes: str) -> str:
    """Valida e retorna o parametro ?mes=YYYY-MM."""
    if not mes or not re.match(r"^\d{4}-\d{2}$", mes):
        abort(400, description="parâmetro 'mes' deve estar no formato YYYY-MM")
    return mes


def validate_modo(modo: str) -> str:
    """Valida o modo de um comprovante em relatorio | gastos | vendas."""
    raw = (modo or "").strip().lower()
    normalizado = _MODO_ALIASES.get(raw)

    if normalizado is None:
        permitidos = ", ".join(sorted(_MODO_ALIASES.keys()))
        abort(400, description=f"parâmetro 'modo' inválido. Use: {permitidos}")

    return normalizado


def validate_comprovante_payload(body: dict) -> dict:
    """Valida o corpo da requisicao do upsert de um comprovante."""
    operacao_raw = str(body.get("operacao", "")).strip().lower()
    operacao = _OPERACAO_ALIASES.get(operacao_raw)
    if operacao is None:
        permitidos = ", ".join(sorted(_OPERACAO_ALIASES.keys()))
        abort(400, description=f"o campo 'operacao' está inválido. Use: {permitidos}")

    item = normalize_non_empty_text(
        body.get("item", ""),
        "item",
        "o campo 'item' não pode ser vazio",
    )
    item_hash = normalize_non_empty_text(
        body.get("item_hash", ""),
        "item_hash",
        "o campo 'item_hash' não pode ser vazio",
    )

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

    # PL fields (optional — MEI doesn't use them)
    def _normalize_optional_field(value):
        if value is None or value == "":
            return None
        normalized = str(value).strip()
        return normalized if normalized else None

    pagador_nome = _normalize_optional_field(body.get("pagador_nome"))
    pagador_cpf = _normalize_optional_field(body.get("pagador_cpf"))
    atendido_nome = _normalize_optional_field(body.get("atendido_nome"))
    atendido_cpf = _normalize_optional_field(body.get("atendido_cpf"))
    natureza_pagamento = _normalize_optional_field(body.get("natureza_pagamento"))

    body["operacao"] = operacao
    body["item"] = item
    body["item_hash"] = item_hash
    body["pagador_nome"] = pagador_nome
    body["pagador_cpf"] = pagador_cpf
    body["atendido_nome"] = atendido_nome
    body["atendido_cpf"] = atendido_cpf
    body["natureza_pagamento"] = natureza_pagamento
    return body
