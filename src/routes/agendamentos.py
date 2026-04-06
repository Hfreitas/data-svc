from datetime import date

from flask import Blueprint, request

from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.config import Config
from src.utils.validators import require_fields, validate_semana_agendamento
import src.queries.agendamentos as q
from src.utils.api_response import ok

agendamentos_bp = Blueprint("agendamentos", __name__)


@agendamentos_bp.route("/usuarios/<int:usuario_id>/agendamentos", methods=["GET"])
def list_agendamentos(usuario_id: int):
    semana = validate_semana_agendamento(request.args.get("semana"))
    iso = date.today().isocalendar()
    semana_iso = f"{iso.year}-W{iso.week:02d}"
    
    agendamentos = cache_get("agendamentos", f"{usuario_id}:{semana_iso}")
    if agendamentos:
        return ok(200, agendamentos) 
    
    with get_db_conn() as conn:
        agendamentos = q.list_semana(conn, usuario_id)
        
        cache_set("agendamentos", f"{usuario_id}:{semana_iso}", agendamentos, Config.CACHE_TTL_AGENDAMENTOS)
        
        return ok(200, agendamentos)


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
