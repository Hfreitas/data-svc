from psycopg2.extras import RealDictCursor


def fetch_persona(conn) -> str | None:
    return fetch_config(conn, "persona")


def fetch_config(conn, chave: str) -> str | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT conteudo FROM agente_config WHERE chave = %s", (chave,)
        )
        row = cur.fetchone()
    return row["conteudo"] if row else None
