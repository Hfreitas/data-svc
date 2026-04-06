from psycopg2.extras import RealDictCursor

"""
Queries de comprovantes — funções puras que recebem conn + parâmetros e retornam rows.
"""


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
    modo = {"gastos": "gasto", "vendas": "venda"}.get(modo, modo)
    
    sql = """
        SELECT
            id,
            operacao,
            item,
            quantidade,
            valor_unitario,
            valor_total,
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
    }
    
    sql = """
        INSERT INTO public.comprovantes (
            usuario_id, item, quantidade, valor_unitario, valor_total,
            data_compra, data_venda, operacao, last_update, item_hash)
        VALUES (
            %(usuario_id)s, %(item)s, %(quantidade)s, %(valor_unitario)s, %(valor_total)s,
            %(data_compra)s, %(data_venda)s, %(operacao)s, NOW(), %(item_hash)s)
        ON CONFLICT (item_hash)
        DO UPDATE SET
            quantidade    = EXCLUDED.quantidade,
            valor_unitario = EXCLUDED.valor_unitario,
            valor_total   = EXCLUDED.valor_total,
            last_update   = EXCLUDED.last_update
        RETURNING id, operacao, item, valor_total, data_compra, data_venda;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row)
    
