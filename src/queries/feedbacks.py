from psycopg2.extras import RealDictCursor


def fetch_feedbacks(conn, usuario_id: int, limit: int = 50, offset: int = 0) -> dict:
    """Lista feedbacks de um usuário com paginação e total."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, usuario_id, texto, classificacao, resolvido, acao_tomada, created_at
            FROM public.feedbacks
            WHERE usuario_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (usuario_id, limit, offset),
        )
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) as total FROM public.feedbacks WHERE usuario_id = %s", (usuario_id,))
        total = cur.fetchone()["total"]

    return {
        "feedbacks": [dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def fetch_feedback_by_id(conn, usuario_id: int, feedback_id: int) -> dict | None:
    """Busca feedback específico garantindo que pertence ao usuário."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, usuario_id, texto, classificacao, resolvido, acao_tomada, created_at
            FROM public.feedbacks
            WHERE id = %s AND usuario_id = %s
            """,
            (feedback_id, usuario_id),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def insert_feedback(conn, usuario_id: int, body: dict) -> dict:
    """Insere novo feedback com todos os campos de triagem."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO public.feedbacks (usuario_id, texto, classificacao, resolvido, acao_tomada)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, usuario_id, texto, classificacao, resolvido, acao_tomada, created_at
            """,
            (
                usuario_id,
                body["texto"],
                body.get("classificacao"),
                body.get("resolvido", False),
                body.get("acao_tomada"),
            ),
        )
        row = cur.fetchone()
    return dict(row)


def update_feedback(conn, usuario_id: int, feedback_id: int, body: dict) -> dict | None:
    """Atualiza campos de resolução de um feedback existente."""
    updates = []
    params = []
    for campo in ("texto", "classificacao", "resolvido", "acao_tomada"):
        if campo in body:
            updates.append(f"{campo} = %s")
            params.append(body[campo])

    if not updates:
        return None

    params.extend([feedback_id, usuario_id])
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            UPDATE public.feedbacks
            SET {', '.join(updates)}
            WHERE id = %s AND usuario_id = %s
            RETURNING id, usuario_id, texto, classificacao, resolvido, acao_tomada, created_at
            """,
            params,
        )
        row = cur.fetchone()
    return dict(row) if row else None


def fetch_feedbacks_resumo(conn, mes_referencia: str) -> dict | None:
    """Busca resumo mensal pelo formato YYYY-MM (convertido para primeiro dia do mês)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, mes_referencia, total_feedbacks, resolvidos_na_hora, payload_resumo, created_at
            FROM public.feedbacks_resumo
            WHERE mes_referencia = %s::date
            """,
            (f"{mes_referencia}-01",),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def insert_feedbacks_resumo(conn, body: dict) -> dict:
    """Insere resumo mensal de feedbacks para envio ao fundador."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO public.feedbacks_resumo (mes_referencia, total_feedbacks, resolvidos_na_hora, payload_resumo)
            VALUES (%s::date, %s, %s, %s)
            RETURNING id, mes_referencia, total_feedbacks, resolvidos_na_hora, payload_resumo, created_at
            """,
            (
                f"{body['mes_referencia']}-01",
                body.get("total_feedbacks", 0),
                body.get("resolvidos_na_hora", 0),
                body.get("payload_resumo"),
            ),
        )
        row = cur.fetchone()
    return dict(row)
