from flask import Blueprint, request, jsonify

from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.config import Config
from src.utils.validators import validate_telefone, require_fields
import src.queries.usuarios as q

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
            return jsonify({"error": "usuario_nao_encontrado"}), 404
        
        cache_set("usuario", telefone, usuario, Config.CACHE_TTL_USUARIO)
        return jsonify(usuario)



@usuarios_bp.route("/usuarios", methods=["POST"])
def create_usuario():
    # TODO: implementar
    # 1. validar body (numero_telefone, nome, razao_social)
    # 2. chamar q.upsert(conn, body)
    # 3. invalidar cache 'usuario:{telefone}'
    # 4. retornar 200 com dados do usuário
    pass


@usuarios_bp.route("/usuarios/<int:usuario_id>", methods=["PUT"])
def update_usuario(usuario_id: int):
    # TODO: implementar
    # 1. validar body (pelo menos um campo permitido presente)
    # 2. chamar q.update(conn, usuario_id, body)
    # 3. invalidar cache 'usuario:{telefone}' e 'usuario:id:{id}'
    # 4. retornar 200 com dados atualizados ou 404
    pass
