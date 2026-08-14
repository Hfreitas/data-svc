"""
Queries de comprovantes — funções puras que recebem conn + parâmetros e retornam rows.
"""
from psycopg2.extras import RealDictCursor


def get_saldo(conn, usuario_id: int, mes: str) -> dict:
    sql = """
        SELECT
            COALESCE(SUM(CASE WHEN operacao = 'venda' THEN valor_total END), 0)::numeric(14,2) AS total_vendas,
            COALESCE(SUM(CASE WHEN operacao = 'gasto' THEN valor_total END), 0)::numeric(14,2) AS total_gastos,
            (COALESCE(SUM(CASE WHEN operacao = 'venda' THEN valor_total END), 0)
            - COALESCE(SUM(CASE WHEN operacao = 'gasto' THEN valor_total END), 0))::numeric(14,2) AS saldo
        FROM public.comprovantes
        WHERE usuario_id = %(usuario_id)s
        AND (
            (operacao = 'venda'
            AND data_venda >= date_trunc('month', TO_DATE(%(referencia)s, 'YYYY-MM'))
            AND data_venda  < date_trunc('month', TO_DATE(%(referencia)s, 'YYYY-MM')) + INTERVAL '1 month')
            OR
            (operacao = 'gasto'
            AND data_compra >= date_trunc('month', TO_DATE(%(referencia)s, 'YYYY-MM'))
            AND data_compra  < date_trunc('month', TO_DATE(%(referencia)s, 'YYYY-MM')) + INTERVAL '1 month')
        );
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id, "referencia": mes})
        row = cursor.fetchone()
        return dict(row)


def list_comprovantes(conn, usuario_id: int, mes: str, modo: str) -> list[dict]:
    modo = modo.strip().lower()

    sql = """
        SELECT
            id,
            operacao,
            item,
            quantidade,
            valor_unitario,
            valor_total,
            canal_venda,
        CASE
            WHEN operacao = 'gasto' THEN data_compra
            WHEN operacao = 'venda' THEN data_venda
        END AS data_lancamento
        FROM public.comprovantes
        WHERE usuario_id = %(usuario_id)s
        AND (
            -- filtro de modo: 'relatorio' traz tudo; 'gastos' só gastos; 'vendas' só vendas
            %(modo)s = 'relatorio'
            OR operacao = %(modo)s  -- 'gastos' → 'gasto'; 'vendas' → 'venda' (normalizar no código)
        )
        AND CASE
            WHEN operacao = 'gasto' THEN data_compra
            WHEN operacao = 'venda' THEN data_venda
        END >= date_trunc('month', TO_DATE(%(referencia)s, 'YYYY-MM'))
        AND CASE
            WHEN operacao = 'gasto' THEN data_compra
            WHEN operacao = 'venda' THEN data_venda
        END < date_trunc('month', TO_DATE(%(referencia)s, 'YYYY-MM')) + INTERVAL '1 month'
        ORDER BY data_lancamento DESC;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id, "modo": modo, "referencia": mes})
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    


def upsert(conn, usuario_id: int, data: dict) -> dict:
    params = {
        "usuario_id": usuario_id,
        "item": data.get("item"),
        "quantidade": data.get("quantidade"),
        "valor_unitario": data.get("valor_unitario"),
        "valor_total": data.get("valor_total"),
        "operacao": data.get("operacao"),
        "item_hash": data.get("item_hash"),
        "data_venda": data.get("data_venda"),
        "data_compra": data.get("data_compra"),
        "canal_venda": data.get("canal_venda"),
        "pagador_nome": data.get("pagador_nome"),
        "pagador_cpf": data.get("pagador_cpf"),
        "atendido_nome": data.get("atendido_nome"),
        "atendido_cpf": data.get("atendido_cpf"),
        "natureza_pagamento": data.get("natureza_pagamento"),
    }

    sql = """
        INSERT INTO public.comprovantes (
            usuario_id, item, quantidade, valor_unitario, valor_total,
            data_compra, data_venda, operacao, last_update, item_hash, canal_venda,
            pagador_nome, pagador_cpf, atendido_nome, atendido_cpf, natureza_pagamento)
        VALUES (
            %(usuario_id)s, %(item)s, %(quantidade)s, %(valor_unitario)s, %(valor_total)s,
            %(data_compra)s, %(data_venda)s, %(operacao)s, NOW(), %(item_hash)s, %(canal_venda)s,
            %(pagador_nome)s, %(pagador_cpf)s, %(atendido_nome)s, %(atendido_cpf)s, %(natureza_pagamento)s)
        ON CONFLICT (item_hash)
        DO UPDATE SET
            quantidade    = EXCLUDED.quantidade,
            valor_unitario = EXCLUDED.valor_unitario,
            valor_total   = EXCLUDED.valor_total,
            last_update   = EXCLUDED.last_update,
            canal_venda   = EXCLUDED.canal_venda,
            pagador_nome  = EXCLUDED.pagador_nome,
            pagador_cpf   = EXCLUDED.pagador_cpf,
            atendido_nome = EXCLUDED.atendido_nome,
            atendido_cpf  = EXCLUDED.atendido_cpf,
            natureza_pagamento = EXCLUDED.natureza_pagamento
        RETURNING id, operacao, item, valor_total, data_compra, data_venda, canal_venda,
                  pagador_nome, pagador_cpf, atendido_nome, atendido_cpf, natureza_pagamento;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row)


def update_ultimo(conn, usuario_id: int, valor_total=None, item=None) -> dict | None:
    """Atualiza o último comprovante de um usuário (por last_update DESC)."""
    params = {
        "usuario_id": usuario_id,
        "valor_total": valor_total,
        "item": item,
    }

    sql = """
        UPDATE public.comprovantes SET
            valor_total = COALESCE(%(valor_total)s, valor_total),
            valor_unitario = COALESCE(%(valor_total)s, valor_unitario),
            item = COALESCE(%(item)s, item),
            last_update = NOW()
        WHERE id = (SELECT id FROM public.comprovantes WHERE usuario_id=%(usuario_id)s ORDER BY last_update DESC LIMIT 1)
        RETURNING id, operacao, item, valor_total;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_ultimo(conn, usuario_id: int) -> dict | None:
    """Deleta o último comprovante de um usuário (por last_update DESC)."""
    params = {"usuario_id": usuario_id}

    sql = """
        DELETE FROM public.comprovantes
        WHERE id = (SELECT id FROM public.comprovantes WHERE usuario_id=%(usuario_id)s ORDER BY last_update DESC LIMIT 1)
        RETURNING id;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def get_ultimo(conn, usuario_id: int) -> dict | None:
    """Retorna o último comprovante de um usuário (por last_update DESC)."""
    params = {"usuario_id": usuario_id}

    sql = """
        SELECT id, operacao, item, quantidade, valor_unitario, valor_total,
               to_char(COALESCE(data_venda, data_compra),'DD/MM/YY') AS data_fmt,
               pagador_nome, atendido_nome, natureza_pagamento
        FROM public.comprovantes
        WHERE usuario_id=%(usuario_id)s
        ORDER BY last_update DESC LIMIT 1;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def get_livro_caixa(conn, usuario_id: int, mes: str) -> dict:
    """Agrega dados do livro de caixa para um mês específico."""
    params = {
        "usuario_id": usuario_id,
        "mes": mes,
    }

    sql = """
        SELECT
            COALESCE(SUM(valor_total) FILTER (WHERE operacao='venda'),0)::numeric(14,2) AS total_rendimentos,
            COALESCE(SUM(valor_total) FILTER (WHERE operacao='gasto'),0)::numeric(14,2) AS total_pagamentos,
            (COALESCE(SUM(valor_total) FILTER (WHERE operacao='venda'),0)
             - COALESCE(SUM(valor_total) FILTER (WHERE operacao='gasto'),0))::numeric(14,2) AS saldo,
            COUNT(*) FILTER (WHERE operacao='venda') AS total_sessoes,
            COALESCE(AVG(valor_total) FILTER (WHERE operacao='venda'),0)::numeric(14,2) AS ticket_medio
        FROM public.comprovantes
        WHERE usuario_id=%(usuario_id)s
            AND to_char(COALESCE(data_venda,data_compra),'YYYY-MM') = %(mes)s;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row)

