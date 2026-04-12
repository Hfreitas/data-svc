"""
Queries de listas de compras — funções puras que recebem conn + parâmetros e retornam rows.
"""
import json

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
    sql = """
        INSERT INTO public.itens_lista (lista_id, nome_item, quantidade, preco_unitario)
        SELECT
            %(lista_id)s,
            LOWER(TRIM(item->>'nome_item')),
            COALESCE(NULLIF(TRIM(item->>'quantidade'), ''), '1')::numeric,
            COALESCE(NULLIF(TRIM(item->>'preco_unitario'), ''), '0')::numeric
        FROM json_array_elements(%(itens)s::json) AS item
        WHERE EXISTS (
            SELECT 1
            FROM public.lista_compras lc
            WHERE lc.id = %(lista_id)s AND lc.usuario_id = %(usuario_id)s
        )
        ON CONFLICT (lista_id, nome_item)
        DO UPDATE SET
            quantidade     = EXCLUDED.quantidade,
            preco_unitario = EXCLUDED.preco_unitario
        RETURNING nome_item, quantidade, preco_unitario;
    """

    params = {
        "lista_id": lista_id,
        "usuario_id": usuario_id,
        "itens": json.dumps(itens),
    }

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def delete_itens(conn, lista_id: int, usuario_id: int, nomes: list[str]) -> list[str]:
    sql = """
        WITH deleted AS (
            DELETE FROM public.itens_lista
            WHERE lista_id = %(lista_id)s
              AND LOWER(TRIM(nome_item)) = ANY(%(nomes)s)
              AND EXISTS (
                SELECT 1 FROM public.lista_compras lc
                WHERE lc.id = %(lista_id)s AND lc.usuario_id = %(usuario_id)s)
            RETURNING nome_item
        )
        SELECT COALESCE(array_agg(nome_item), ARRAY[]::text[]) AS removidos
        FROM deleted;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"lista_id": lista_id, "usuario_id": usuario_id, "nomes": nomes})
        row = cursor.fetchone()
        return list(row["removidos"]) if row and row["removidos"] else []
