"""
Queries de agendamentos — funções puras que recebem conn + parâmetros e retornam rows.
"""


def list_semana(conn, usuario_id: int) -> list[dict]:
    # TODO: implementar
    # Executar SELECT para a semana atual (segunda a sábado) no fuso America/Sao_Paulo
    # Retornar lista de dicts ordenada por data_compromisso, hora_compromisso
    pass


def create(conn, usuario_id: int, data: dict) -> dict:
    # TODO: implementar
    # Executar INSERT RETURNING
    # Converter data_compromisso via TO_DATE(%(data_compromisso)s, 'DD/MM/YYYY')
    # Retornar dict com dados do agendamento criado
    pass


def update_status(conn, agendamento_id: int, usuario_id: int, status: str) -> dict | None:
    # TODO: implementar
    # Executar UPDATE status WHERE id AND usuario_id RETURNING
    # Retornar dict ou None se não encontrado
    pass
