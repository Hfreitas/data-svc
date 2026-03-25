"""
Queries de listas de compras — funções puras que recebem conn + parâmetros e retornam rows.
"""


def list_listas(conn, usuario_id: int) -> list[dict]:
    # TODO: implementar
    # Executar SELECT lc + COUNT itens LEFT JOIN
    # Retornar lista de dicts { id, nome_lista, total_itens }
    pass


def list_itens(conn, lista_id: int, usuario_id: int) -> list[dict]:
    # TODO: implementar
    # Executar SELECT verificando ownership via EXISTS
    # Retornar lista de dicts { id, nome_item, quantidade, preco_unitario, preco_total }
    pass


def upsert_itens(conn, lista_id: int, usuario_id: int, itens: list[dict]) -> list[dict]:
    # TODO: implementar
    # Executar INSERT ... ON CONFLICT (lista_id, nome_item) DO UPDATE via json_array_elements
    # Retornar lista de dicts com itens inseridos/atualizados
    pass


def delete_itens(conn, lista_id: int, usuario_id: int, nomes: list[str]) -> list[str]:
    # TODO: implementar
    # Executar DELETE WHERE nome_item = ANY e ownership via EXISTS
    # Retornar lista de nomes removidos
    pass
