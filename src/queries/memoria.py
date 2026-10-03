from psycopg2.extras import RealDictCursor


def fetch_memoria_12h(conn, usuario_id: int, limit: int = 50) -> dict:
    """Janela de memória de conversa: 12h.

    O número vem do apagador, não daqui: `cron.job` id 3 (STG e PRD) roda de hora
    em hora e apaga `chat_memory` com mais de 12h. A query pedia 2 dias, então a
    faixa entre 12h e 48h era sempre vazia — nome e SQL prometiam contexto que o
    banco já tinha removido. Ao mexer neste intervalo, mexa no cron junto.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT papel, conteudo, criado_em
            FROM chat_memory
            WHERE usuario_id = %s
              AND criado_em > NOW() - INTERVAL '12 hours'
            ORDER BY criado_em DESC
            LIMIT %s
            """,
            (usuario_id, limit),
        )
        rows = cur.fetchall()
        rows.reverse()  # DESC+LIMIT pega as N mais recentes; reverte pra ordem cronológica

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
