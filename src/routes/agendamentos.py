from flask import Blueprint, request, jsonify

from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.config import Config
from src.utils.validators import require_fields
import src.queries.agendamentos as q

agendamentos_bp = Blueprint("agendamentos", __name__)


@agendamentos_bp.route("/usuarios/<int:usuario_id>/agendamentos", methods=["GET"])
def list_agendamentos(usuario_id: int):
    # TODO: implementar
    # 1. extrair ?semana=atual (por ora apenas "atual" suportado)
    # 2. calcular semana ISO atual
    # 3. checar cache 'agendamentos:{usuario_id}:{semana_iso}'
    # 4. chamar q.list_semana(conn, usuario_id)
    # 5. armazenar no cache com TTL CACHE_TTL_AGENDAMENTOS
    # 6. retornar lista de agendamentos
    pass


@agendamentos_bp.route("/usuarios/<int:usuario_id>/agendamentos", methods=["POST"])
def create_agendamento(usuario_id: int):
    # TODO: implementar
    # 1. validar body (nome_compromisso, data_compromisso, hora_compromisso)
    # 2. chamar q.create(conn, usuario_id, body)
    # 3. invalidar cache 'agendamentos:{usuario_id}:*'
    # 4. retornar 201 com dados do agendamento criado
    pass


@agendamentos_bp.route(
    "/usuarios/<int:usuario_id>/agendamentos/<int:agendamento_id>", methods=["PUT"]
)
def update_agendamento(usuario_id: int, agendamento_id: int):
    # TODO: implementar
    # 1. validar body (status obrigatório)
    # 2. chamar q.update_status(conn, agendamento_id, usuario_id, status)
    # 3. invalidar cache 'agendamentos:{usuario_id}:*'
    # 4. retornar 200 com dados atualizados ou 404
    pass
