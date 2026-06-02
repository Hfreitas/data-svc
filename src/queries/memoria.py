from psycopg2.extras import RealDictCursor


def fetch_memoria_24h(conn, usuario_id: int, limit: int = 50) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT papel, conteudo, criado_em
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
        nome = "MEI" if row["papel"] == "user" else "MEIrelles"
        linhas.append(f"[{hora}] {nome}: {row['conteudo']}")

    return {"memoria": "\n".join(linhas), "total": len(rows)}


def insert_memoria(conn, usuario_id: int, body: dict) -> dict:
    nome_agente = body.get("agent_name", "pivo")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO chat_memory (usuario_id, sessao_id, papel, conteudo, nome_agente)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (usuario_id, body["session_id"], body["role"], body["content"], nome_agente),
        )
        row = cur.fetchone()
    return {"id": row["id"]}
