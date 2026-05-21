from typing import List
from psycopg2.extras import RealDictCursor


def busca_semantica(
    conn, embedding: List[float], threshold: float, count: int
) -> list:
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM documents
            WHERE 1 - (embedding <=> %s::vector) > %s
            ORDER BY similarity DESC
            LIMIT %s
            """,
            (embedding_str, embedding_str, threshold, count),
        )
        rows = cur.fetchall()
    return [
        {"id": r["id"], "content": r["content"], "similarity": float(r["similarity"])}
        for r in rows
    ]
