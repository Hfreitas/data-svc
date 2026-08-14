from flask import Blueprint, request

from src.cache import cache_get, cache_set, get_cache
from src.db import get_db_conn
from src.utils.validators import (
    validate_bairro_lookup_params,
    validate_ranking_params,
    validate_resposta_conexao_payload,
    validate_solicitante_id,
    validate_telefone_param,
)
import src.queries.comunidade as q
from src.utils.api_response import fail, ok

comunidade_bp = Blueprint("comunidade", __name__)

_BAIRRO_NS = "comunidade_bairro"
_BAIRRO_TTL = 3600

# get_cache fixa o TTL na criação do namespace; se o primeiro acesso fosse um
# cache_get, o namespace nasceria com DEFAULT_TTL (60s). Pinar aqui, no import.
get_cache(_BAIRRO_NS, ttl=_BAIRRO_TTL)


@comunidade_bp.route("/comunidade/profissionais/ranking", methods=["GET"])
def ranking_profissionais():
    params = validate_ranking_params(request.args)

    with get_db_conn() as conn:
        resultado = q.ranking(conn, **params)
        return ok(200, resultado)


@comunidade_bp.route("/comunidade/bairros", methods=["GET"])
def resolver_bairro():
    """Resolve bairro por nome explícito (`?nome=`) ou varrendo a mensagem (`?texto=`).

    Dado de referência, lido em todo turno de busca -> cache L1 (nunca L2: o volume
    é pequeno e a tabela é local ao processo). Não cacheia miss, senão um bairro
    recém-cadastrado ficaria invisível por 1h.
    """
    params = validate_bairro_lookup_params(request.args)
    chave = f"nome:{params['nome']}" if params["nome"] else f"texto:{params['texto']}"

    cached = cache_get(_BAIRRO_NS, chave)
    if cached is not None:
        return ok(200, cached)

    with get_db_conn() as conn:
        bairro = q.buscar_bairro(conn, **params)

    if bairro is None:
        return fail("bairro_nao_encontrado", status_code=404)

    cache_set(_BAIRRO_NS, chave, bairro, ttl=_BAIRRO_TTL)
    return ok(200, bairro)


@comunidade_bp.route("/comunidade/conexoes", methods=["GET"])
def listar_conexoes():
    """Histórico de conexões do solicitante. SEM cache — ver docstring de pendente()."""
    solicitante_id = validate_solicitante_id(request.args)

    with get_db_conn() as conn:
        return ok(200, q.conexoes_do_usuario(conn, solicitante_id))


@comunidade_bp.route("/comunidade/conexoes/pendente", methods=["GET"])
def conexao_pendente():
    """Conexão aguardando o SIM do indicado, pelo telefone DELE.

    SEM cache, de propósito: esta rota é lida e mutada no mesmo fluxo de
    consentimento duplo (PATCH etapa=1/2). Ler estado velho aqui = mandar vCard de
    quem ainda não aceitou. É bug de privacidade, não de performance.
    """
    telefone = validate_telefone_param(request.args)

    with get_db_conn() as conn:
        conexao = q.conexao_pendente_por_telefone(conn, telefone)

    if conexao is None:
        return fail("conexao_pendente_nao_encontrada", status_code=404)
    return ok(200, conexao)


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
