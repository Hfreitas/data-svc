from flask import Blueprint, request
from src.db import get_db_conn
from src.utils.api_response import ok, fail

bp = Blueprint("chat_memory", __name__)

@bp.route("/chat-memory", methods=["GET"])
def get_chat_memory():
    usuario_id = request.args.get("usuario_id")
    if not usuario_id:
        return fail("usuario_id_obrigatorio", 400)
    try:
        usuario_id = int(usuario_id)
    except ValueError:
        return fail("usuario_id_invalido", 400)
    limit = request.args.get("limit", 20, type=int)
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT papel, conteudo, criado_em
                FROM chat_memory
                WHERE usuario_id = %s
                ORDER BY criado_em DESC
                LIMIT %s
            """, (usuario_id, limit))
            rows = cur.fetchall()
            historico = [{"role": r[0], "content": r[1], "criado_em": r[2].isoformat()} for r in reversed(rows)]
            return ok(200, historico)

@bp.route("/chat-memory", methods=["POST"])
def post_chat_memory():
    body = request.get_json()
    if not body or not all(k in body for k in ("usuario_id", "role", "content")):
        return fail("campos_faltando", "usuario_id, role e content são obrigatórios", 400)
    usuario_id = body["usuario_id"]
    role = body["role"]
    content = body["content"]
    if role not in ("user", "assistant"):
        return fail("role_invalida", "role deve ser 'user' ou 'assistant'", 400)
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_memory (usuario_id, papel, conteudo)
                VALUES (%s, %s, %s)
                RETURNING id, criado_em
            """, (usuario_id, role, content))
            row = cur.fetchone()
            conn.commit()
            return ok(201, {"id": row[0], "criado_em": row[1].isoformat()})
