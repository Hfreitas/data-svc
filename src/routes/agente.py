from flask import Blueprint
from src.db import get_db_conn
from src.cache import cache_get, cache_set
from src.utils.api_response import ok, fail
import src.queries.agente as queries

agente_bp = Blueprint("agente", __name__)

_CHAVES_VALIDAS = {"persona", "pivo"}


@agente_bp.get("/agente/persona")
def get_persona():
    return _get_config("persona", "persona")


@agente_bp.get("/agente/<chave>")
def get_config(chave):
    if chave not in _CHAVES_VALIDAS:
        return fail("not_found", f"Configuração '{chave}' não existe", 404)
    return _get_config(chave, chave)


def _get_config(chave: str, campo: str):
    cached = cache_get("agente", chave)
    if cached:
        return ok(200, cached)
    with get_db_conn() as conn:
        conteudo = queries.fetch_config(conn, chave)
    if conteudo is None:
        return fail("not_found", f"'{chave}' não configurado", 404)
    resultado = {campo: conteudo}
    cache_set("agente", chave, resultado, ttl=3600)
    return ok(200, resultado)
