"""
Queries de contas recorrentes — funções puras que recebem conn + parâmetros e retornam rows.
"""

TIPOS_VALIDOS = {"aluguel", "internet", "luz", "agua", "boleto"}


def upsert(conn, usuario_id: int, data: dict) -> dict:
    # TODO: implementar
    # Executar INSERT ... ON CONFLICT (usuario_id, tipo) WHERE tipo <> 'boleto' DO UPDATE
    # Retornar dict com dados da conta
    pass
