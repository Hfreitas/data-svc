from flask import Blueprint, request

from src.db import get_db_conn
from src.cache import cache_get, cache_invalidate_prefix, cache_set
from src.config import Config
from src.utils.validators import validate_agendamento_payload, validate_scope_agendamento, validate_update_agendamento_payload, validate_recurrence_payload, validate_conflict_check_params
from src.utils.recurrence_generator import generate_recurrence_dates
import src.queries.agendamentos as q
from src.utils.api_response import fail, ok

agendamentos_bp = Blueprint("agendamentos", __name__)


@agendamentos_bp.route("/usuarios/<int:usuario_id>/agendamentos", methods=["GET"])
def list_agendamentos(usuario_id: int):
    scope = validate_scope_agendamento(request.args.get("scope"))

    cache_key = f"{usuario_id}:{scope}"
    agendamentos = cache_get("agendamentos", cache_key)
    if agendamentos:
        return ok(200, agendamentos)

    with get_db_conn() as conn:
        agendamentos = q.list_agendamentos(conn, usuario_id)

        cache_set("agendamentos", cache_key, agendamentos, Config.CACHE_TTL_AGENDAMENTOS)

        return ok(200, agendamentos)


@agendamentos_bp.route("/usuarios/<int:usuario_id>/agendamentos/conflitos", methods=["GET"])
def check_conflicts(usuario_id: int):
    data = request.args.get("data")
    hora = request.args.get("hora")
    nome_compromisso = request.args.get("nome_compromisso")
    
    data_obj, hora_str, nome_str = validate_conflict_check_params(data, hora, nome_compromisso)
    
    with get_db_conn() as conn:
        resultado = q.check_conflicts(conn, usuario_id, data_obj, hora_str, nome_str)
        return ok(200, resultado)


@agendamentos_bp.route("/usuarios/<int:usuario_id>/agendamentos", methods=["POST"])
def create_agendamento(usuario_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)
    
    body = validate_agendamento_payload(body)
    
    with get_db_conn() as conn:
        agendamento = q.create(conn, usuario_id, body)
        
        cache_invalidate_prefix("agendamentos", f"{usuario_id}:")
        
        return ok(201 ,agendamento)


@agendamentos_bp.route("/usuarios/<int:usuario_id>/agendamentos/recorrentes", methods=["POST"])
def create_recurrence(usuario_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)
    
    validated_data = validate_recurrence_payload(body)
    
    try:
        datas = generate_recurrence_dates(
            validated_data["data_inicio"],
            validated_data["frequencia"],
            validated_data["dia_semana_ou_mes"],
            validated_data["quantidade_meses"]
        )
    except ValueError as e:
        return fail("recurrence_generation_error", str(e), 400)
    
    if not datas:
        return fail("no_dates_generated", "Nenhuma data foi gerada para a recorrência", 400)
    
    with get_db_conn() as conn:
        agendamentos = q.create_recurrence(
            conn,
            usuario_id,
            validated_data["nome_compromisso"],
            datas,
            validated_data["hora_compromisso"]
        )
        
        cache_invalidate_prefix("agendamentos", f"{usuario_id}:")
        
        return ok(201, agendamentos)


@agendamentos_bp.route(
    "/usuarios/<int:usuario_id>/agendamentos/<int:agendamento_id>", methods=["PUT"]
)
def update_agendamento(usuario_id: int, agendamento_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)
    
    validated_data = validate_update_agendamento_payload(body)
    
    with get_db_conn() as conn:
        agendamento = q.update(conn, agendamento_id, usuario_id, validated_data)
        
        if agendamento is None:
            return fail("agendamento_nao_encontrado", f"o agendamento com id {agendamento_id} para o usuário informado não foi encontrado", status_code=404)
        
        cache_invalidate_prefix("agendamentos", f"{usuario_id}:")
        
        return ok(200, agendamento)


@agendamentos_bp.route("/usuarios/<int:usuario_id>/agendamentos", methods=["DELETE"])
def cancel_all_agendamentos(usuario_id: int):
    with get_db_conn() as conn:
        agendamentos_cancelados = q.cancel_all(conn, usuario_id)
        
        cache_invalidate_prefix("agendamentos", f"{usuario_id}:")
        
        return ok(200, agendamentos_cancelados)


@agendamentos_bp.route("/usuarios/<int:usuario_id>/agendamentos/recorrencia/<string:recorrencia_id>", methods=["DELETE"])
def cancel_recurrence(usuario_id: int, recorrencia_id: str):
    with get_db_conn() as conn:
        agendamentos_cancelados = q.cancel_recurrence(conn, usuario_id, recorrencia_id)
        
        cache_invalidate_prefix("agendamentos", f"{usuario_id}:")
        
        return ok(200, agendamentos_cancelados)
