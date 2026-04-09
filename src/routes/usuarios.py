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
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    allowed_fields = {
        "nome", "razao_social", "estado_atual", "interacao_previa",
        "tipo_negocio", "descricao_negocio", "descricao_objetivo",
        "area_ajuda", "preco_referencia", "dias_trabalho",
        "horario_inicio", "horario_fim", "data_ultimo_contato"            
    }
    
    fields_to_update = {
        k: v for k, v in body.items()
        if k in allowed_fields and v is not None
    }
    
    if not fields_to_update:
        return fail(
            "campos_invalidos",
            "informe ao menos um campo permitido",
            400,
        )
    
    with get_db_conn() as conn:
               
        usuario = q.update(conn, usuario_id, fields_to_update)
        if not usuario:
            return fail("usuario_nao_encontrado", status_code=404)

        cache_invalidate("usuario", usuario["numero_telefone"])
        cache_invalidate("usuario", f"id:{usuario_id}")

        return ok(200, usuario)

