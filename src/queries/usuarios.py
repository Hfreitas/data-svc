"""
Queries de usuários — funções puras que recebem conn + parâmetros e retornam rows.
Nenhuma lógica HTTP ou de cache aqui.
"""


def find_by_telefone(conn, telefone: str) -> dict | None:
    # TODO: implementar
    # Executar SELECT por numero_telefone, retornar dict ou None
    pass


def upsert(conn, numero_telefone: str, nome: str, razao_social: str) -> dict:
    # TODO: implementar
    # Executar CTE: existing_user + inserted_user (evita race condition)
    # Retornar dict com dados do usuário (existente ou recém-criado)
    pass


def update(conn, usuario_id: int, fields: dict) -> dict | None:
    # TODO: implementar
    # Executar UPDATE com COALESCE para campos permitidos
    # Retornar dict com dados atualizados ou None se não encontrado
    pass
