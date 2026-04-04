from psycopg2.extras import RealDictCursor

"""
Queries de comprovantes — funções puras que recebem conn + parâmetros e retornam rows.
"""


def get_saldo(conn, usuario_id: int, mes: str) -> dict:
    # Executar SELECT SUM por operacao filtrado pelo mês
    # Retornar { total_vendas, total_gastos, saldo }
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
    # TODO: implementar
    # modo: 'relatorio' | 'gastos' | 'vendas'
    # Normalizar modo: 'gastos' → 'gasto', 'vendas' → 'venda'
    # Executar SELECT filtrado por mes e modo
    # Retornar lista de dicts
    pass


def upsert(conn, usuario_id: int, data: dict) -> dict:
    # TODO: implementar
    # Executar INSERT ... ON CONFLICT (item_hash) DO UPDATE
    # Retornar dict com dados do comprovante
    pass
