"""
Queries de contas recorrentes — funções puras que recebem conn + parâmetros e retornam rows.
"""
from psycopg2.extras import RealDictCursor


def list_by_usuario(conn, usuario_id: int) -> list:
    sql = """
        SELECT id, tipo, descricao, valor, dia_vencimento, lembrete_ativo, ativo, created_at
        FROM public.contas_recorrentes
        WHERE usuario_id = %(usuario_id)s AND ativo = true
        ORDER BY tipo, descricao;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"usuario_id": usuario_id})
        return [dict(r) for r in cur.fetchall()]


def upsert(conn, usuario_id: int, data: dict) -> dict:
    params = {
        "usuario_id": usuario_id,
        "tipo": data.get("tipo"),
        "descricao": data.get("descricao"),
        "valor": data.get("valor"),
        "dia_vencimento": data.get("dia_vencimento"),
        "lembrete_ativo": data.get("lembrete_ativo", False),
        "pix_chave": data.get("pix_chave"),
    }

    sql = """
        INSERT INTO public.contas_recorrentes (
            usuario_id, tipo, descricao, valor, dia_vencimento, lembrete_ativo, pix_chave)
        VALUES (
            %(usuario_id)s,
            %(tipo)s,        -- 'aluguel' | 'internet' | 'luz' | 'agua' | 'boleto'
            %(descricao)s,
            %(valor)s,
            %(dia_vencimento)s,
            %(lembrete_ativo)s,
            %(pix_chave)s)
        ON CONFLICT (usuario_id, tipo) WHERE tipo <> 'boleto'
        DO UPDATE SET
            descricao      = EXCLUDED.descricao,
            valor          = EXCLUDED.valor,
            dia_vencimento = EXCLUDED.dia_vencimento,
            lembrete_ativo = EXCLUDED.lembrete_ativo,
            pix_chave      = EXCLUDED.pix_chave,
            updated_at     = NOW()
        RETURNING id, tipo, descricao, valor, dia_vencimento, lembrete_ativo;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row)


def patch(conn, conta_id: int, usuario_id: int, data: dict) -> dict | None:
    """Atualiza parcialmente uma conta recorrente.

    Args:
        conn: Conexão postgres
        conta_id: ID da conta
        usuario_id: ID do usuário (verificação de segurança)
        data: Dict com campos para atualizar (já validados)

    Returns:
        Dict com a conta atualizada ou None se não encontrada.
    """
    _PATCHABLE = {"descricao", "valor", "dia_vencimento", "lembrete_ativo", "ativo"}

    updates = {k: v for k, v in data.items() if k in _PATCHABLE}

    if not updates:
        return None

    set_clause = ", ".join(f"{k} = %({k})s" for k in updates)
    updates["conta_id"] = conta_id
    updates["usuario_id"] = usuario_id

    sql = f"""
        UPDATE public.contas_recorrentes
        SET {set_clause}, updated_at = NOW()
        WHERE id = %(conta_id)s AND usuario_id = %(usuario_id)s
        RETURNING id, tipo, descricao, valor, dia_vencimento, lembrete_ativo, ativo;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, updates)
        row = cur.fetchone()
        return dict(row) if row else None
