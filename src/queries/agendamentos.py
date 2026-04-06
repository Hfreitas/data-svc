from psycopg2.extras import RealDictCursor

"""
Queries de agendamentos — funções puras que recebem conn + parâmetros e retornam rows.
"""


def list_semana(conn, usuario_id: int) -> list[dict]:
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
            AND data_compromisso >= date_trunc('week', NOW() AT TIME ZONE 'America/Sao_Paulo')::date
            AND data_compromisso <  date_trunc('week', NOW() AT TIME ZONE 'America/Sao_Paulo')::date + INTERVAL '7 day'
        ORDER BY data_compromisso, hora_compromisso;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id})
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    


def create(conn, usuario_id: int, data: dict) -> dict:
    params ={
        "usuario_id": usuario_id,
        "nome_compromisso": data.get("nome_compromisso"),    
        "data_compromisso": data.get("data_compromisso"),
        "hora_compromisso": data.get("hora_compromisso")
    }
    
    sql = """
        INSERT INTO public.agendamentos (
            usuario_id, nome_compromisso, data_compromisso,
            hora_compromisso, status, data_criacao, data_modificacao)
        VALUES (
            %(usuario_id)s,
            %(nome_compromisso)s,
            %(data_compromisso)s::date,
            %(hora_compromisso)s::time,
            'confirmado',
            NOW(), NOW())
        RETURNING id, nome_compromisso, data_compromisso, hora_compromisso, status;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row)


def update_status(conn, agendamento_id: int, usuario_id: int, status: str) -> dict | None:
    # TODO: implementar
    # Executar UPDATE status WHERE id AND usuario_id RETURNING
    # Retornar dict ou None se não encontrado
    pass
