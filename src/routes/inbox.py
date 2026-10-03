from flask import Blueprint, request

from src.db import get_db_conn
from src.utils.api_response import fail, ok
import src.queries.inbox as q

inbox_bp = Blueprint("inbox", __name__)


def _json_body():
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


# ============ ACCOUNTS ============

@inbox_bp.route("/inbox/accounts", methods=["POST"])
def create_account():
    body = _json_body()
    if body is None:
        return fail("body_invalido", "JSON inválido ou ausente", 400)
    if not body.get("phone_number"):
        return fail("phone_number_obrigatorio", "phone_number é obrigatório", 400)

    with get_db_conn() as conn:
        account = q.create_account(conn, body)
        return ok(201, account)


@inbox_bp.route("/inbox/accounts/by-phone/<string:phone>", methods=["GET"])
def get_account_by_phone(phone: str):
    with get_db_conn() as conn:
        account = q.get_account_by_phone(conn, phone)
        if account is None:
            return fail("account_nao_encontrada", f"nenhuma conta para o número {phone}", 404)
        return ok(200, account)


@inbox_bp.route("/inbox/accounts/<int:account_id>/conversations", methods=["GET"])
def list_conversations(account_id: int):
    status = request.args.get("status")
    with get_db_conn() as conn:
        conversas = q.list_conversations(conn, account_id, status)
        return ok(200, conversas)


# ============ CONTACTS ============

@inbox_bp.route("/inbox/accounts/<int:account_id>/contacts", methods=["POST"])
def upsert_contact(account_id: int):
    body = _json_body()
    if body is None:
        return fail("body_invalido", "JSON inválido ou ausente", 400)
    if not body.get("phone_number"):
        return fail("phone_number_obrigatorio", "phone_number é obrigatório", 400)

    with get_db_conn() as conn:
        contact = q.upsert_contact(conn, account_id, body)
        return ok(201, contact)


# ============ CONVERSATIONS ============

@inbox_bp.route("/inbox/conversations", methods=["POST"])
def open_conversation():
    """Abre (ou retorna) a conversa aberta de um contato — idempotente p/ inbound."""
    body = _json_body()
    if body is None:
        return fail("body_invalido", "JSON inválido ou ausente", 400)
    account_id = body.get("account_id")
    contact_id = body.get("contact_id")
    if not account_id or not contact_id:
        return fail("params_obrigatorios", "account_id e contact_id são obrigatórios", 400)

    with get_db_conn() as conn:
        conversa = q.open_or_get_conversation(conn, account_id, contact_id)
        return ok(201, conversa)


@inbox_bp.route("/inbox/conversations/<int:conversation_id>/messages", methods=["GET"])
def list_messages(conversation_id: int):
    try:
        limit = min(int(request.args.get("limit", 50)), 200)
    except (TypeError, ValueError):
        return fail("limit_invalido", "limit deve ser inteiro", 400)
    before_id = request.args.get("before_id", type=int)

    with get_db_conn() as conn:
        mensagens = q.list_messages(conn, conversation_id, limit, before_id)
        return ok(200, mensagens)


# ============ MESSAGES ============

@inbox_bp.route("/inbox/messages", methods=["POST"])
def create_message():
    body = _json_body()
    if body is None:
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    if not body.get("conversation_id"):
        return fail("conversation_id_obrigatorio", "conversation_id é obrigatório", 400)

    sender_type = body.get("sender_type")
    if sender_type not in ("user", "contact"):
        return fail("sender_type_invalido", "sender_type deve ser 'user' ou 'contact'", 400)
    if sender_type == "user" and not body.get("sender_id"):
        return fail("sender_id_obrigatorio", "sender_id é obrigatório quando sender_type='user'", 400)

    with get_db_conn() as conn:
        message = q.create_message(conn, body)
        return ok(201, message)
