import json
from typing import List
from psycopg2.extras import RealDictCursor


def busca_semantica(
    conn, embedding: List[float], threshold: float, count: int, perfil: str | None = None
) -> list:
    """Busca vetorial em documents.

    Se `perfil` (mei|autonomo|pl) informado, filtra por `metadata.perfil`: retorna
    chunks taggeados com esse perfil OU sem tag de perfil (conteúdo geral/compartilhado).
    Evita, ex., devolver chunk MEI-only (DAS) pra um PL.
    """
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    params: list = [embedding_str, embedding_str, threshold]

    perfil_clause = ""
    if perfil:
        # @> testa se o array metadata.perfil contém o perfil; NOT (? 'perfil') = chunk sem tag (geral)
        perfil_clause = " AND (metadata->'perfil' @> %s::jsonb OR NOT (metadata ? 'perfil'))"
        params.append(json.dumps([perfil]))

    params.append(count)
    sql = f"""
        SELECT id, content,
               1 - (embedding <=> %s::vector) AS similarity
        FROM documents
        WHERE 1 - (embedding <=> %s::vector) > %s{perfil_clause}
        ORDER BY similarity DESC
        LIMIT %s
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [
        {"id": r["id"], "content": r["content"], "similarity": float(r["similarity"])}
        for r in rows
    ]
