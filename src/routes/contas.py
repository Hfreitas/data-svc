from flask import Blueprint, request

from src.db import get_db_conn
from src.utils.validators import validate_conta_recorrente_payload, validate_patch_conta_payload
import src.queries.contas as q
from src.utils.api_response import fail, ok

contas_bp = Blueprint("contas", __name__)


@contas_bp.route("/usuarios/<int:usuario_id>/contas-recorrentes", methods=["GET"])
def list_contas(usuario_id: int):
    with get_db_conn() as conn:
        contas = q.list_by_usuario(conn, usuario_id)
        return ok(200, contas)


@contas_bp.route("/usuarios/<int:usuario_id>/contas-recorrentes", methods=["POST"])
def upsert_conta(usuario_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    body = validate_conta_recorrente_payload(body)

    with get_db_conn() as conn:
        conta = q.upsert(conn, usuario_id, body)
        return ok(200, conta)


@contas_bp.route("/usuarios/<int:usuario_id>/contas-recorrentes/<int:conta_id>", methods=["PATCH"])
def patch_conta(usuario_id: int, conta_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    body = validate_patch_conta_payload(body)

    with get_db_conn() as conn:
        conta = q.patch(conn, conta_id, usuario_id, body)
        if not conta:
            return fail("conta_nao_encontrada", status_code=404)
        return ok(200, conta)
