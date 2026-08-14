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


def buscar_bairro(conn, nome: str | None = None, texto: str | None = None) -> dict | None:
    """Resolve um bairro da Comunidade.

    `nome`  — nome dito explicitamente (match exato, senão LIKE).
    `texto` — mensagem livre do usuário; casa qualquer bairro citado dentro dela e
              devolve a ÚLTIMA menção (maior `position`), que é a mais recente na frase.
              Substitui a lista de bairros hardcoded que vivia no n8n.
    """
    if nome:
        sql = """
            SELECT id, nome, cidade, uf, centro_lat, centro_lon
            FROM public.comunidade_bairros
            WHERE ativo AND (lower(nome) = lower(%(nome)s)
                             OR lower(nome) LIKE '%%' || lower(%(nome)s) || '%%')
            ORDER BY (lower(nome) = lower(%(nome)s)) DESC
            LIMIT 1;
        """
        params = {"nome": nome}
    else:
        sql = """
            SELECT id, nome, cidade, uf, centro_lat, centro_lon
            FROM public.comunidade_bairros
            WHERE ativo AND position(lower(nome) in lower(%(texto)s)) > 0
            ORDER BY position(lower(nome) in lower(%(texto)s)) DESC
            LIMIT 1;
        """
        params = {"texto": texto}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


def conexoes_do_usuario(conn, solicitante_id: int, limite: int = 30) -> list:
    """Histórico de conexões do solicitante, com os dois lados já montados em JSON."""
    sql = """
        SELECT
          c.id, c.status, c.profissional_resposta, c.servico_contexto,
          c.created_at AS data_conexao, c.conectado_em,
          jsonb_build_object(
            'nome', COALESCE(ps.nome_exibicao, us.nome),
            'telefone', us.numero_telefone,
            'negocio', COALESCE(us.razao_social, ps.nome_exibicao, us.nome)
          ) AS profissional_1,
          jsonb_build_object(
            'nome', COALESCE(pp.nome_exibicao, up.nome),
            'telefone', up.numero_telefone,
            'negocio', COALESCE(up.razao_social, pp.nome_exibicao, up.nome),
            'profissional_id', pp.id
          ) AS profissional_2
        FROM public.comunidade_conexoes c
        JOIN public.comunidade_profissionais pp ON pp.id = c.profissional_id
        JOIN public.usuarios up                 ON up.id = pp.usuario_id
        JOIN public.usuarios us                 ON us.id = c.solicitante_usuario_id
        LEFT JOIN public.comunidade_profissionais ps ON ps.usuario_id = c.solicitante_usuario_id
        WHERE c.solicitante_usuario_id = %(solicitante_id)s
        ORDER BY c.updated_at DESC
        LIMIT %(limite)s;
    """
    params = {"solicitante_id": solicitante_id, "limite": limite}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def conexao_pendente_por_telefone(conn, telefone: str) -> dict | None:
    """Conexão aguardando o SIM do indicado, buscada pelo telefone DELE.

    Comparação com os dois lados normalizados (só dígitos) — o telefone chega do
    WhatsApp sem máscara e o cadastro pode ter máscara.
    """
    sql = """
        SELECT
          c.id, c.status, c.solicitante_usuario_id, c.profissional_id, c.servico_contexto,
          regexp_replace(us.numero_telefone, '\\D', '', 'g') AS solicitante_telefone,
          us.nome                                            AS solicitante_nome,
          COALESCE(us.razao_social, us.nome)                 AS solicitante_negocio,
          regexp_replace(up.numero_telefone, '\\D', '', 'g') AS indicado_telefone,
          COALESCE(pp.nome_exibicao, up.nome)                AS indicado_nome,
          COALESCE(up.razao_social, pp.nome_exibicao, up.nome) AS indicado_negocio,
          pp.usuario_id                                      AS indicado_usuario_id
        FROM public.comunidade_conexoes c
        JOIN public.comunidade_profissionais pp ON pp.id = c.profissional_id
        JOIN public.usuarios up                 ON up.id = pp.usuario_id
        JOIN public.usuarios us                 ON us.id = c.solicitante_usuario_id
        WHERE c.status = 'aguardando_profissional'
          AND COALESCE(c.profissional_resposta, false) = false
          AND regexp_replace(up.numero_telefone, '\\D', '', 'g')
              = regexp_replace(%(telefone)s, '\\D', '', 'g')
        ORDER BY c.updated_at DESC
        LIMIT 1;
    """
    params = {"telefone": telefone}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


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
