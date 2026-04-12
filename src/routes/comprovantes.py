from flask import Blueprint, request

from src.db import get_db_conn
from src.cache import cache_get, cache_invalidate_prefix, cache_set
from src.config import Config
from src.utils.validators.validator_comprovantes import (
    validate_comprovante_payload,
    validate_mes,
    validate_modo,
)
import src.queries.comprovantes as q
from src.utils.api_response import fail, ok

comprovantes_bp = Blueprint("comprovantes", __name__)


@comprovantes_bp.route("/usuarios/<int:usuario_id>/saldo", methods=["GET"])
def get_saldo(usuario_id: int):
    mes = validate_mes(request.args.get("mes"))
    
    saldo_mes = cache_get("saldo", f"{usuario_id}:{mes}")
    if saldo_mes:
        return ok(200, saldo_mes)
    
    with get_db_conn() as conn:
        saldo_mes = q.get_saldo(conn, usuario_id, mes)     

        cache_set("saldo", f"{usuario_id}:{mes}", saldo_mes, Config.CACHE_TTL_SALDO)
        
        return ok(200, saldo_mes)
    


@comprovantes_bp.route("/usuarios/<int:usuario_id>/comprovantes", methods=["GET"])
def list_comprovantes(usuario_id: int):
    mes = validate_mes(request.args.get("mes"))
    modo = validate_modo(request.args.get("modo"))  
    
    comprovantes = cache_get("comprovantes", f"{usuario_id}:{mes}:{modo}")
    if comprovantes:
        return ok(200, comprovantes)
    
    with get_db_conn() as conn:
        comprovantes = q.list_comprovantes(conn, usuario_id, mes, modo)
        
        cache_set("comprovantes", f"{usuario_id}:{mes}:{modo}", comprovantes, Config.CACHE_TTL_COMPROVANTES)
        
        return ok(200, comprovantes)


@comprovantes_bp.route("/usuarios/<int:usuario_id>/comprovantes", methods=["POST"])
def create_comprovante(usuario_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)
    
    body = validate_comprovante_payload(body)
    
    with get_db_conn() as conn:
        comprovante = q.upsert(conn, usuario_id, body)
        
        cache_invalidate_prefix("saldo", f"{usuario_id}:")
        cache_invalidate_prefix("comprovantes", f"{usuario_id}:")
        
        return ok(200, comprovante)
        

    
