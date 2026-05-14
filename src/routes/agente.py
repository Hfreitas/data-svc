from flask import Blueprint
from src.db import get_db_conn
from src.cache import cache_get, cache_set
from src.utils.api_response import ok, fail
import src.queries.agente as queries

agente_bp = Blueprint("agente", __name__)


@agente_bp.get("/agente/persona")
def get_persona():
    cached = cache_get("agente", "persona")
    if cached:
        return ok(200, cached)
    with get_db_conn() as conn:
        conteudo = queries.fetch_persona(conn)
    if conteudo is None:
        return fail("not_found", "Persona não configurada", 404)
    resultado = {"persona": conteudo}
    cache_set("agente", "persona", resultado, ttl=3600)
    return ok(200, resultado)
