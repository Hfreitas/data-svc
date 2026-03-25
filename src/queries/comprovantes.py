"""
Queries de comprovantes — funções puras que recebem conn + parâmetros e retornam rows.
"""


def get_saldo(conn, usuario_id: int, mes: str) -> dict:
    # TODO: implementar
    # Executar SELECT SUM por operacao filtrado pelo mês
    # Retornar { total_vendas, total_gastos, saldo }
    pass


def list_comprovantes(conn, usuario_id: int, mes: str, modo: str) -> list[dict]:
    # TODO: implementar
    # modo: 'relatorio' | 'gastos' | 'vendas'
    # Normalizar modo: 'gastos' → 'gasto', 'vendas' → 'venda'
    # Executar SELECT filtrado por mes e modo
    # Retornar lista de dicts
    pass


def upsert(conn, usuario_id: int, data: dict) -> dict:
    # TODO: implementar
    # Executar INSERT ... ON CONFLICT (item_hash) DO UPDATE
    # Retornar dict com dados do comprovante
    pass
