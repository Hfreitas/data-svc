import json
from typing import List
from psycopg2.extras import RealDictCursor


def busca_semantica(
    conn,
    embedding: List[float],
    threshold: float,
    count: int,
    perfil: str | None = None,
    source_prefix: str | None = None,
) -> list:
    """Busca vetorial em documents.

    Se `perfil` (mei|autonomo|pl) informado, filtra por `metadata.perfil`: retorna
    chunks taggeados com esse perfil OU sem tag de perfil (conteúdo geral/compartilhado).
    Evita, ex., devolver chunk MEI-only (DAS) pra um PL.

    Se `source_prefix` informado (ex. ``knowledge_duvidas``), restringe a
    ``metadata.source LIKE '{prefix}%'``. Sem isso, a KB de produto
    (``knowledge_mei.md`` — planos/cardápio) compete com o guia fiscal e
    ganha no ranking por palavras como "valor" (incidente 190, 2026-09-14).
    """
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    params: list = [embedding_str, embedding_str, threshold]

    perfil_clause = ""
    if perfil:
        # @> testa se o array metadata.perfil contém o perfil; NOT (? 'perfil') = chunk sem tag (geral)
        perfil_clause = " AND (metadata->'perfil' @> %s::jsonb OR NOT (metadata ? 'perfil'))"
        params.append(json.dumps([perfil]))

    source_clause = ""
    if source_prefix:
        # só alfanumérico/underscore/hífen — evita LIKE injection
        safe = "".join(c for c in str(source_prefix) if c.isalnum() or c in "_-.")
        if safe:
            source_clause = " AND metadata->>'source' LIKE %s"
            params.append(safe + "%")

    params.append(count)
    sql = f"""
        SELECT id, content,
               1 - (embedding <=> %s::vector) AS similarity
        FROM documents
        WHERE 1 - (embedding <=> %s::vector) > %s{perfil_clause}{source_clause}
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
