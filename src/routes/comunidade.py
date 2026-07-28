from flask import Blueprint, request

from src.db import get_db_conn
from src.utils.validators import validate_ranking_params, validate_resposta_conexao_payload
import src.queries.comunidade as q
from src.utils.api_response import fail, ok

comunidade_bp = Blueprint("comunidade", __name__)


@comunidade_bp.route("/comunidade/profissionais/ranking", methods=["GET"])
def ranking_profissionais():
    params = validate_ranking_params(request.args)

    with get_db_conn() as conn:
        resultado = q.ranking(conn, **params)
        return ok(200, resultado)


@comunidade_bp.route("/comunidade/conexoes/<uuid:conexao_id>/resposta", methods=["PATCH"])
def responder_conexao(conexao_id):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    body = validate_resposta_conexao_payload(body)

    fn = q.responder_solicitante if body["etapa"] == 1 else q.responder_profissional

    with get_db_conn() as conn:
        resultado = fn(conn, conexao_id, body["resposta"])
        if resultado is None:
            return fail("conexao_nao_encontrada_para_transicao", status_code=404)
        return ok(200, resultado)
