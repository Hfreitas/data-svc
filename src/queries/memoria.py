from psycopg2.extras import RealDictCursor


def fetch_memoria_24h(conn, usuario_id: int, limit: int = 50) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT role, content, criado_em
            FROM chat_memory
            WHERE usuario_id = %s
              AND criado_em > NOW() - INTERVAL '1 day'
            ORDER BY criado_em ASC
            LIMIT %s
            """,
            (usuario_id, limit),
        )
        rows = cur.fetchall()

    linhas = []
    for row in rows:
        hora = row["criado_em"].strftime("%H:%M")
        nome = "MEI" if row["role"] == "user" else "MEIrelles"
        linhas.append(f"[{hora}] {nome}: {row['content']}")

    return {"memoria": "\n".join(linhas), "total": len(rows)}


def insert_memoria(conn, usuario_id: int, body: dict) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO chat_memory (usuario_id, session_id, role, content)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (usuario_id, body["session_id"], body["role"], body["content"]),
        )
        row = cur.fetchone()
    return {"id": row["id"]}
