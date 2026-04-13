from flask import abort


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
