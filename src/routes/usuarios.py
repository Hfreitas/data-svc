from flask import Blueprint, request, jsonify

from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.config import Config
from src.utils.validators import validate_telefone, require_fields
import src.queries.usuarios as q

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.route("/usuarios", methods=["GET"])
def get_usuario():
    # TODO: implementar
    # 1. validar query param ?telefone=
    # 2. checar cache 'usuario:{telefone}'
    # 3. chamar q.find_by_telefone(conn, telefone)
    # 4. armazenar no cache com TTL CACHE_TTL_USUARIO
    # 5. retornar 200 ou 404
    pass


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
