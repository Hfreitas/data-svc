"""
Queries de Comunidade MEIrelles — matching entre profissionais MEI cadastrados
(ex: motoboy, bolos) por bairro/categoria, com fluxo de conexão em duas etapas.
"""
from psycopg2.extras import RealDictCursor


def ranking(
    conn,
    bairro_id: int,
    categoria: str,
    solicitante_id: int,
    limite: int = 3,
    servico_contexto: str | None = None,
) -> list:
    sql = """
        WITH origem AS (
          SELECT centro_lat, centro_lon FROM public.comunidade_bairros WHERE id = %(bairro_id)s
        )
        SELECT
          p.id                                           AS profissional_id,
          COALESCE(p.nome_exibicao, u.nome)               AS nome,
          p.servico_categoria,
          p.servico_descricao,
          b.nome                                          AS bairro,
          round((6371 * acos(
              least(1, greatest(-1,
                cos(radians(o.centro_lat)) * cos(radians(b.centro_lat)) *
                cos(radians(b.centro_lon) - radians(o.centro_lon)) +
                sin(radians(o.centro_lat)) * sin(radians(b.centro_lat))
              ))
          ))::numeric, 1)                                 AS distancia_km
        FROM public.comunidade_profissionais p
        JOIN public.comunidade_bairros b ON b.id = p.bairro_id
        JOIN public.usuarios u           ON u.id = p.usuario_id
        CROSS JOIN origem o
        WHERE p.ativo AND p.aceita_ser_contatado
          AND p.servico_categoria = %(categoria)s
          AND p.usuario_id <> %(solicitante_id)s
          AND NOT EXISTS (
            SELECT 1 FROM public.comunidade_conexoes c
            WHERE c.solicitante_usuario_id = %(solicitante_id)s AND c.profissional_id = p.id
              AND c.status IN ('pendente','aguardando_profissional','conectado'))
        ORDER BY distancia_km ASC, random()
        LIMIT %(limite)s;
    """
    params = {
        "bairro_id": bairro_id,
        "categoria": categoria,
        "solicitante_id": solicitante_id,
        "limite": limite,
    }

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]

    for row in rows:
        row["conexao_id"] = _upsert_conexao_pendente(
            conn, solicitante_id, row["profissional_id"], servico_contexto
        )

    return rows


def _upsert_conexao_pendente(conn, solicitante_id: int, profissional_id: int, servico_contexto: str | None) -> str:
    sql = """
        INSERT INTO public.comunidade_conexoes (solicitante_usuario_id, profissional_id, servico_contexto)
        VALUES (%(solicitante_id)s, %(profissional_id)s, %(servico_contexto)s)
        ON CONFLICT (solicitante_usuario_id, profissional_id)
          WHERE status IN ('pendente','aguardando_profissional')
        DO UPDATE SET updated_at = now()
        RETURNING id;
    """
    params = {
        "solicitante_id": solicitante_id,
        "profissional_id": profissional_id,
        "servico_contexto": servico_contexto,
    }

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return str(row["id"])


def responder_solicitante(conn, conexao_id, resposta: bool) -> dict | None:
    sql = """
        UPDATE public.comunidade_conexoes
        SET status = CASE WHEN %(resposta)s THEN 'aguardando_profissional' ELSE 'recusado_solicitante' END,
            solicitante_resposta = %(resposta)s, solicitante_respondeu_em = now(), updated_at = now()
        WHERE id = %(conexao_id)s AND status = 'pendente'
        RETURNING id, status;
    """
    params = {"conexao_id": conexao_id, "resposta": resposta}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


def responder_profissional(conn, conexao_id, resposta: bool) -> dict | None:
    sql = """
        UPDATE public.comunidade_conexoes
        SET status = CASE WHEN %(resposta)s THEN 'conectado' ELSE 'recusado_profissional' END,
            profissional_resposta = %(resposta)s, profissional_respondeu_em = now(),
            conectado_em = CASE WHEN %(resposta)s THEN now() ELSE NULL END, updated_at = now()
        WHERE id = %(conexao_id)s AND status = 'aguardando_profissional'
        RETURNING id, status;
    """
    params = {"conexao_id": conexao_id, "resposta": resposta}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None
