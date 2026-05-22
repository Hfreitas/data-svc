from flask import Blueprint, request
from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate, cache_invalidate_prefix
from src.utils.api_response import ok, fail
from src.config import Config
import src.queries.feedbacks as queries

feedbacks_bp = Blueprint("feedbacks", __name__)

# Valores válidos mapeados aos agentes especializados do MEIrelles (feedback.md)
_CLASSIFICACOES_VALIDAS = {
    "Agente 2 — Onboarding",
    "Agente 3 — Contador",
    "Agente 4 — Business",
    "Agente 5 — Agenda",
    "Agente 6 — Pagamento",
    "Agente 7 — NF",
    "Agente 8 — Políticas",
    "Agente 9 — Objetivo",
    "Geral — MEIrelles",
}


@feedbacks_bp.post("/feedbacks")
def post_feedback_flat():
    """Salva feedback do agente — usuario_id no body (interface primária para N8N)."""
    body = request.get_json()
    if not body:
        return fail("invalid_body", "Body JSON obrigatório", 400)
    if "usuario_id" not in body:
        return fail("missing_field", "Campo obrigatório: usuario_id", 400)
    if "texto" not in body:
        return fail("missing_field", "Campo obrigatório: texto", 400)
    if body.get("classificacao") and body["classificacao"] not in _CLASSIFICACOES_VALIDAS:
        return fail("invalid_classificacao", f"classificacao inválida: {body['classificacao']}", 400)
    usuario_id = int(body["usuario_id"])
    with get_db_conn() as conn:
        novo = queries.insert_feedback(conn, usuario_id, body)
    cache_invalidate_prefix("feedbacks", f"{usuario_id}:")
    return ok(201, novo)


@feedbacks_bp.get("/usuarios/<int:id>/feedbacks")
def get_feedbacks(id):
    """Lista feedbacks de um usuário com paginação opcional."""
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    cache_key = f"{id}:{offset}:{limit}"
    cached = cache_get("feedbacks", cache_key)
    if cached:
        return ok(200, cached)
    with get_db_conn() as conn:
        resultado = queries.fetch_feedbacks(conn, id, limit, offset)
    cache_set("feedbacks", cache_key, resultado, Config.CACHE_TTL_FEEDBACKS)
    return ok(200, resultado)


@feedbacks_bp.get("/usuarios/<int:id>/feedbacks/<int:feedback_id>")
def get_feedback(id, feedback_id):
    """Retorna feedback individual garantindo pertencimento ao usuário."""
    cache_key = f"{id}:single:{feedback_id}"
    cached = cache_get("feedbacks", cache_key)
    if cached:
        return ok(200, cached)
    with get_db_conn() as conn:
        resultado = queries.fetch_feedback_by_id(conn, id, feedback_id)
    if not resultado:
        return fail("not_found", "Feedback não encontrado", 404)
    cache_set("feedbacks", cache_key, resultado, Config.CACHE_TTL_FEEDBACKS)
    return ok(200, resultado)


@feedbacks_bp.put("/usuarios/<int:id>/feedbacks/<int:feedback_id>")
def put_feedback(id, feedback_id):
    """Atualiza campos de resolução (resolvido, acao_tomada, classificacao)."""
    body = request.get_json()
    if not body:
        return fail("invalid_body", "Body JSON obrigatório", 400)
    if body.get("classificacao") and body["classificacao"] not in _CLASSIFICACOES_VALIDAS:
        return fail("invalid_classificacao", f"classificacao inválida: {body['classificacao']}", 400)
    with get_db_conn() as conn:
        atualizado = queries.update_feedback(conn, id, feedback_id, body)
    if not atualizado:
        return fail("not_found", "Feedback não encontrado", 404)
    cache_invalidate_prefix("feedbacks", f"{id}:")
    cache_invalidate("feedbacks", f"{id}:single:{feedback_id}")
    return ok(200, atualizado)


@feedbacks_bp.get("/feedbacks/resumo/<mes_referencia>")
def get_feedbacks_resumo(mes_referencia):
    """Retorna resumo mensal por YYYY-MM (ex: 2026-05)."""
    cache_key = f"resumo:{mes_referencia}"
    cached = cache_get("feedbacks", cache_key)
    if cached:
        return ok(200, cached)
    with get_db_conn() as conn:
        resultado = queries.fetch_feedbacks_resumo(conn, mes_referencia)
    if not resultado:
        return fail("not_found", "Resumo não encontrado para o mês informado", 404)
    cache_set("feedbacks", cache_key, resultado, ttl=3600)
    return ok(200, resultado)


@feedbacks_bp.post("/feedbacks/resumo")
def post_feedbacks_resumo():
    """Persiste resumo mensal consolidado para envio ao fundador."""
    body = request.get_json()
    if not body:
        return fail("invalid_body", "Body JSON obrigatório", 400)
    if "mes_referencia" not in body:
        return fail("missing_field", "Campo obrigatório: mes_referencia (YYYY-MM)", 400)
    with get_db_conn() as conn:
        novo = queries.insert_feedbacks_resumo(conn, body)
    cache_invalidate("feedbacks", f"resumo:{body['mes_referencia']}")
    return ok(201, novo)
