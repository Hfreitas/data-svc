from flask import Blueprint, request, jsonify

from src.db import get_db_conn
from src.utils.validators import require_fields
import src.queries.contas as q

contas_bp = Blueprint("contas", __name__)


@contas_bp.route("/usuarios/<int:usuario_id>/contas-recorrentes", methods=["POST"])
def upsert_conta(usuario_id: int):
    # TODO: implementar
    # 1. validar body (tipo, descricao, valor, dia_vencimento)
    # 2. validar tipo: 'aluguel' | 'internet' | 'luz' | 'agua' | 'boleto'
    # 3. chamar q.upsert(conn, usuario_id, body)
    # 4. retornar 200 com dados da conta (sem cache — dados raramente lidos pelo N8N diretamente)
    pass
