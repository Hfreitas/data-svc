from flask import Blueprint, request, jsonify

from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.config import Config
from src.utils.validators import validate_telefone, require_fields
import src.queries.usuarios as q
from src.utils.api_response import fail, ok

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.route("/usuarios", methods=["GET"])
def get_usuario():
    telefone = validate_telefone(request.args.get('telefone')) 
      
    cached = cache_get("usuario", telefone)
    
    if cached:
        return jsonify(cached)
    
    with get_db_conn() as conn:
        usuario = q.find_by_telefone(conn, telefone)
        
        if not usuario:
            return fail("usuario_nao_encontrado", status_code=404)
        
        cache_set("usuario", telefone, usuario, Config.CACHE_TTL_USUARIO)
        return ok(200, usuario)



@usuarios_bp.route("/usuarios", methods=["POST"])
def create_usuario():
    body = request.get_json()
    
    require_fields(body, "numero_telefone", "nome", "razao_social")
    
    numero_telefone = body["numero_telefone"]
    validate_telefone(numero_telefone)
    
    with get_db_conn() as conn:
        usuario = q.upsert(conn, numero_telefone, body["nome"], body["razao_social"])
        
        cache_invalidate("usuario", numero_telefone)
        
        return ok(200, usuario)


@usuarios_bp.route("/usuarios/<int:usuario_id>", methods=["PUT"])
def update_usuario(usuario_id: int):
    # TODO: implementar
    # 1. validar body (pelo menos um campo permitido presente)
    # 2. chamar q.update(conn, usuario_id, body)
    # 3. invalidar cache 'usuario:{telefone}' e 'usuario:id:{id}'
    # 4. retornar 200 com dados atualizados ou 404
    pass
