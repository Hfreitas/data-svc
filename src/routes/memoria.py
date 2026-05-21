from flask import Blueprint, request
from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.utils.api_response import ok, fail
import src.queries.memoria as queries

memoria_bp = Blueprint("memoria", __name__)

_ROLES_VALIDOS = {"user", "assistant", "system"}


@memoria_bp.get("/usuarios/<int:id>/memoria")
def get_memoria(id):
    limit = int(request.args.get("limit", 50))
    cache_key = f"memoria:{id}"
    cached = cache_get("memoria", cache_key)
    if cached:
        return ok(200, cached)
    with get_db_conn() as conn:
        resultado = queries.fetch_memoria_24h(conn, id, limit)
    cache_set("memoria", cache_key, resultado, ttl=60)
    return ok(200, resultado)


@memoria_bp.post("/usuarios/<int:id>/memoria")
def post_memoria(id):
    body = request.get_json()
    if not body:
        return fail("invalid_body", "Body JSON obrigatório", 400)
    for campo in ("session_id", "role", "content"):
        if campo not in body:
            return fail("missing_field", f"Campo obrigatório: {campo}", 400)
    if body["role"] not in _ROLES_VALIDOS:
        return fail("invalid_role", "role deve ser user, assistant ou system", 400)
    with get_db_conn() as conn:
        novo = queries.insert_memoria(conn, id, body)
    cache_invalidate("memoria", f"memoria:{id}")
    return ok(201, novo)
