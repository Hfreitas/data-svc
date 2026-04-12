from flask import Blueprint, request

from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.config import Config
from src.utils.validators.validator_listas import (
    validate_lista_delete_itens_payload,
    validate_lista_itens_payload,
)
import src.queries.listas as q
from src.utils.api_response import fail, ok

listas_bp = Blueprint("listas", __name__)


@listas_bp.route("/usuarios/<int:usuario_id>/listas", methods=["GET"])
def list_listas(usuario_id: int):
    listas = cache_get("listas", usuario_id)
    if listas:
        return ok(200, listas)
    
    with get_db_conn() as conn:
        listas = q.list_listas(conn, usuario_id)
        
        cache_set("listas", usuario_id, listas, Config.CACHE_TTL_LISTAS)
        
        return ok(200, listas)


@listas_bp.route("/usuarios/<int:usuario_id>/listas/<int:lista_id>/itens", methods=["GET"])
def list_itens(usuario_id: int, lista_id: int):
    itens_lista = cache_get("itens_lista", lista_id)
    if itens_lista:
        return ok(200, itens_lista)
    
    with get_db_conn() as conn:
        itens_lista = q.list_itens(conn, lista_id, usuario_id)
        
        cache_set("itens_lista", lista_id, itens_lista, Config.CACHE_TTL_LISTAS)
        
        return ok(200, itens_lista)


@listas_bp.route("/usuarios/<int:usuario_id>/listas/<int:lista_id>/itens", methods=["POST"])
def upsert_itens(usuario_id: int, lista_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    itens_normalizados = validate_lista_itens_payload(body)

    with get_db_conn() as conn:
        itens_upsertados = q.upsert_itens(conn, lista_id, usuario_id, itens_normalizados)

        cache_invalidate("itens_lista", lista_id)

        return ok(200, itens_upsertados)


@listas_bp.route("/usuarios/<int:usuario_id>/listas/<int:lista_id>/itens", methods=["DELETE"])
def delete_itens(usuario_id: int, lista_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    nomes = validate_lista_delete_itens_payload(body)

    with get_db_conn() as conn:
        removidos = q.delete_itens(conn, lista_id, usuario_id, nomes)

        cache_invalidate("itens_lista", lista_id)

        return ok(200, {"removidos": removidos})
