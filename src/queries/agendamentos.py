from psycopg2.extras import RealDictCursor

"""
Queries de agendamentos — funções puras que recebem conn + parâmetros e retornam rows.
"""


def list_semana(conn, usuario_id: int) -> list[dict]:
    # TODO: implementar
    # Executar SELECT para a semana atual (segunda a sábado) no fuso America/Sao_Paulo
    # Retornar lista de dicts ordenada por data_compromisso, hora_compromisso
    sql = """
        SELECT
            id,
            nome_compromisso,
            data_compromisso,
            TO_CHAR(hora_compromisso, 'HH24:MI') AS hora_compromisso,
            status
        FROM public.agendamentos
        WHERE usuario_id = %(usuario_id)s
            AND status IN ('pendente', 'confirmado', 'agendado')
            AND data_compromisso >= date_trunc('week', CURRENT_DATE AT TIME ZONE 'America/Sao_Paulo')::date
            AND data_compromisso <  date_trunc('week', CURRENT_DATE AT TIME ZONE 'America/Sao_Paulo')::date + 7
        ORDER BY data_compromisso, hora_compromisso;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id})
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    


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
