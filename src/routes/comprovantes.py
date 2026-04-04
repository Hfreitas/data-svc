from flask import Blueprint, request, jsonify

from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.config import Config
from src.utils.validators import validate_mes, require_fields
import src.queries.comprovantes as q
from src.utils.api_response import ok

comprovantes_bp = Blueprint("comprovantes", __name__)


@comprovantes_bp.route("/usuarios/<int:usuario_id>/saldo", methods=["GET"])
def get_saldo(usuario_id: int):
    mes = validate_mes(request.args.get("mes"))
    
    saldo_mes = cache_get("saldo", usuario_id)
    if saldo_mes:
        return ok(200, saldo_mes)
    
    with get_db_conn() as conn:
        saldo_mes = q.get_saldo(conn, usuario_id, mes)     

        cache_set("saldo", usuario_id, saldo_mes, Config.CACHE_TTL_SALDO)
        
        return ok(200, saldo_mes)
    


@comprovantes_bp.route("/usuarios/<int:usuario_id>/comprovantes", methods=["GET"])
def list_comprovantes(usuario_id: int):
    # TODO: implementar
    # 1. validar ?mes=YYYY-MM e ?modo=relatorio|gastos|vendas
    # 2. checar cache 'comprovantes:{usuario_id}:{YYYY-MM}:{modo}'
    # 3. chamar q.list_comprovantes(conn, usuario_id, mes, modo)
    # 4. armazenar no cache com TTL CACHE_TTL_COMPROVANTES
    # 5. retornar lista de comprovantes
    pass


@comprovantes_bp.route("/usuarios/<int:usuario_id>/comprovantes", methods=["POST"])
def create_comprovante(usuario_id: int):
    # TODO: implementar
    # 1. validar body (item, quantidade, valor_unitario, valor_total, operacao, item_hash)
    # 2. chamar q.upsert(conn, usuario_id, body)
    # 3. invalidar cache 'saldo:{usuario_id}:*' e 'comprovantes:{usuario_id}:*'
    # 4. retornar 200 com dados do comprovante inserido/atualizado
    pass
