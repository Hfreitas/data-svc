"""
Queries de listas de compras — funções puras que recebem conn + parâmetros e retornam rows.
"""
from psycopg2.extras import RealDictCursor


def list_listas(conn, usuario_id: int) -> list[dict]:
    sql = """
        SELECT
            lc.id,
            lc.nome_lista,
            COUNT(il.id) AS total_itens
        FROM public.lista_compras lc
        LEFT JOIN public.itens_lista il ON lc.id = il.lista_id
        WHERE lc.usuario_id = %(usuario_id)s
        GROUP BY lc.id, lc.nome_lista
        ORDER BY lc.data_atualizacao DESC;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id})
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def list_itens(conn, lista_id: int, usuario_id: int) -> list[dict]:
    sql = """
        SELECT
            il.id,
            il.nome_item,
            il.quantidade,
            il.preco_unitario,
            il.preco_total
        FROM public.itens_lista il
        WHERE il.lista_id = %(lista_id)s
        AND EXISTS (
            SELECT 1 FROM public.lista_compras lc
            WHERE lc.id = %(lista_id)s AND lc.usuario_id = %(usuario_id)s)
        ORDER BY il.nome_item;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"lista_id": lista_id, "usuario_id": usuario_id})
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    

def upsert_itens(conn, lista_id: int, usuario_id: int, itens: list[dict]) -> list[dict]:
    # TODO: implementar
    # Executar INSERT ... ON CONFLICT (lista_id, nome_item) DO UPDATE via json_array_elements
    # Retornar lista de dicts com itens inseridos/atualizados
    pass


def delete_itens(conn, lista_id: int, usuario_id: int, nomes: list[str]) -> list[str]:
    # TODO: implementar
    # Executar DELETE WHERE nome_item = ANY e ownership via EXISTS
    # Retornar lista de nomes removidos
    pass
