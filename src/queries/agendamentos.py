"""
Queries de agendamentos — funções puras que recebem conn + parâmetros e retornam rows.
"""
from psycopg2.extras import RealDictCursor
import uuid


def list_agendamentos(conn, usuario_id: int) -> list[dict]:
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
            AND (data_compromisso::timestamp + hora_compromisso) > (NOW() AT TIME ZONE 'America/Sao_Paulo')
        ORDER BY data_compromisso, hora_compromisso;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id})
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    


def _find_by_unique_key(cursor, params: dict) -> dict | None:
    sql = """
        SELECT
            id,
            nome_compromisso,
            data_compromisso,
            hora_compromisso,
            status,
            lembrete_minutos_antes
        FROM public.agendamentos
        WHERE usuario_id = %(usuario_id)s
            AND nome_compromisso = %(nome_compromisso)s
            AND data_compromisso = %(data_compromisso)s::date
            AND hora_compromisso = %(hora_compromisso)s::time
        ORDER BY id DESC
        LIMIT 1;
    """
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return dict(row) if row else None


def create(conn, usuario_id: int, data: dict) -> dict:
    """Cria agendamento ou devolve o existente (idempotente na unique constraint)."""
    params = {
        "usuario_id": usuario_id,
        "nome_compromisso": data.get("nome_compromisso"),
        "data_compromisso": data.get("data_compromisso"),
        "hora_compromisso": data.get("hora_compromisso"),
        "lembrete_minutos_antes": data.get("lembrete_minutos_antes", 15),
    }

    sql = """
        INSERT INTO public.agendamentos (
            usuario_id, nome_compromisso, data_compromisso,
            hora_compromisso, status, lembrete_minutos_antes, data_criacao, data_modificacao)
        VALUES (
            %(usuario_id)s,
            %(nome_compromisso)s,
            %(data_compromisso)s::date,
            %(hora_compromisso)s::time,
            'confirmado',
            %(lembrete_minutos_antes)s,
            NOW(), NOW())
        ON CONFLICT ON CONSTRAINT unique_agendamento_por_usuario
        DO NOTHING
        RETURNING id, nome_compromisso, data_compromisso, hora_compromisso, status, lembrete_minutos_antes;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result["created"] = True
            return result

        existing = _find_by_unique_key(cursor, params)
        if existing is None:
            raise RuntimeError(
                "agendamento unique conflict sem registro existente "
                f"(usuario_id={usuario_id})"
            )
        existing["created"] = False
        return existing


def update_status(conn, agendamento_id: int, usuario_id: int, status: str) -> dict | None:
    sql = """
        UPDATE public.agendamentos
        SET status = %(status)s, data_modificacao = NOW()
        WHERE id = %(agendamento_id)s
            AND usuario_id = %(usuario_id)s
        RETURNING id, nome_compromisso, status;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"agendamento_id": agendamento_id, "usuario_id": usuario_id, "status":status})
        row = cursor.fetchone()
        return dict(row) if row else None


def update(conn, agendamento_id: int, usuario_id: int, data: dict) -> dict | None:
    """Atualiza múltiplos campos de um agendamento usando COALESCE para preservar valores originais."""
    params = {
        "agendamento_id": agendamento_id,
        "usuario_id": usuario_id,
        "nome_compromisso": data.get("nome_compromisso"),
        "data_compromisso": data.get("data_compromisso"),
        "hora_compromisso": data.get("hora_compromisso"),
        "status": data.get("status"),
        "lembrete_minutos_antes": data.get("lembrete_minutos_antes"),
    }

    sql = """
        UPDATE public.agendamentos
        SET
            nome_compromisso = COALESCE(%(nome_compromisso)s, nome_compromisso),
            data_compromisso = COALESCE(%(data_compromisso)s::date, data_compromisso),
            hora_compromisso = COALESCE(%(hora_compromisso)s::time, hora_compromisso),
            status = COALESCE(%(status)s, status),
            lembrete_minutos_antes = COALESCE(%(lembrete_minutos_antes)s, lembrete_minutos_antes),
            lembrete_enviado = CASE WHEN %(hora_compromisso)s IS NOT NULL
                                     OR %(data_compromisso)s IS NOT NULL
                                     OR %(lembrete_minutos_antes)s IS NOT NULL
                                THEN FALSE ELSE lembrete_enviado END,
            data_modificacao = NOW()
        WHERE id = %(agendamento_id)s
            AND usuario_id = %(usuario_id)s
        RETURNING id, nome_compromisso, data_compromisso, TO_CHAR(hora_compromisso, 'HH24:MI') AS hora_compromisso, status, lembrete_minutos_antes;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def cancel_all(conn, usuario_id: int) -> list[dict]:
    """Cancela todos os agendamentos ativos do usuário e retorna os itens afetados."""
    sql = """
        UPDATE public.agendamentos
        SET status = 'cancelado', data_modificacao = NOW()
        WHERE usuario_id = %(usuario_id)s
            AND status IN ('pendente', 'confirmado', 'agendado')
        RETURNING nome_compromisso, data_compromisso, TO_CHAR(hora_compromisso, 'HH24:MI') AS hora_compromisso;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id})
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def cancel_recurrence(conn, usuario_id: int, recorrencia_id: str) -> list[dict]:
    """Cancela todos os agendamentos de uma série recorrente e retorna os itens afetados."""
    sql = """
        UPDATE public.agendamentos
        SET status = 'cancelado', data_modificacao = NOW()
        WHERE usuario_id = %(usuario_id)s
            AND recorrencia_id = %(recorrencia_id)s
            AND status IN ('pendente', 'confirmado', 'agendado')
        RETURNING nome_compromisso, data_compromisso, TO_CHAR(hora_compromisso, 'HH24:MI') AS hora_compromisso;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id, "recorrencia_id": recorrencia_id})
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def create_recurrence(conn, usuario_id: int, nome_compromisso: str, datas: list, hora_compromisso: str) -> list[dict]:
    """Cria série recorrente; datas já existentes são reaproveitadas (idempotente)."""
    if not datas:
        return []

    recorrencia_id = str(uuid.uuid4())

    placeholders = []
    params = {
        "usuario_id": usuario_id,
        "nome_compromisso": nome_compromisso,
        "hora_compromisso": hora_compromisso,
        "recorrencia_id": recorrencia_id,
        "status": "confirmado",
    }

    for i, data_compromisso in enumerate(datas):
        params[f"data_{i}"] = data_compromisso
        placeholders.append(
            f"(%(usuario_id)s, %(nome_compromisso)s, %(data_{i})s::date, "
            f"%(hora_compromisso)s::time, %(status)s, %(recorrencia_id)s, NOW(), NOW())"
        )

    sql_insert = f"""
        INSERT INTO public.agendamentos (
            usuario_id, nome_compromisso, data_compromisso,
            hora_compromisso, status, recorrencia_id, data_criacao, data_modificacao)
        VALUES {', '.join(placeholders)}
        ON CONFLICT ON CONSTRAINT unique_agendamento_por_usuario
        DO NOTHING
        RETURNING id;
    """

    data_placeholders = ", ".join(f"%(data_{i})s::date" for i in range(len(datas)))
    sql_select = f"""
        SELECT
            id,
            nome_compromisso,
            data_compromisso,
            TO_CHAR(hora_compromisso, 'HH24:MI') AS hora_compromisso,
            status,
            recorrencia_id
        FROM public.agendamentos
        WHERE usuario_id = %(usuario_id)s
            AND nome_compromisso = %(nome_compromisso)s
            AND hora_compromisso = %(hora_compromisso)s::time
            AND data_compromisso IN ({data_placeholders})
        ORDER BY data_compromisso, id;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql_insert, params)
        inserted_ids = {row["id"] for row in cursor.fetchall()}

        cursor.execute(sql_select, params)
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["created"] = item["id"] in inserted_ids
            results.append(item)
        return results


def check_conflicts(conn, usuario_id: int, data_compromisso, hora_compromisso: str, nome_compromisso: str) -> dict:
    """Verifica se há conflito de horário para um agendamento."""
    sql = """
        SELECT 
            COUNT(*) as total,
            STRING_AGG(nome_compromisso || ' às ' || TO_CHAR(hora_compromisso, 'HH24:MI'), ', ') as descricao
        FROM public.agendamentos
        WHERE usuario_id = %(usuario_id)s
            AND nome_compromisso ILIKE %(nome_compromisso)s
            AND data_compromisso = %(data_compromisso)s::date
            AND hora_compromisso = %(hora_compromisso)s::time
            AND status IN ('pendente', 'confirmado', 'agendado');
    """
    
    params = {
        "usuario_id": usuario_id,
        "nome_compromisso": f"%{nome_compromisso}%",
        "data_compromisso": data_compromisso,
        "hora_compromisso": hora_compromisso,
    }
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        total = row["total"]
        descricao = row["descricao"]
        
        return {
            "conflito": total > 0,
            "total": total,
            "descricao": descricao if total > 0 else None,
        }
