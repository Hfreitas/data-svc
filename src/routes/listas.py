from flask import Blueprint, request, jsonify

from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.config import Config
from src.utils.validators import require_fields
import src.queries.listas as q

listas_bp = Blueprint("listas", __name__)


@listas_bp.route("/usuarios/<int:usuario_id>/listas", methods=["GET"])
def list_listas(usuario_id: int):
    # TODO: implementar
    # 1. checar cache 'listas:{usuario_id}'
    # 2. chamar q.list_listas(conn, usuario_id)
    # 3. armazenar no cache com TTL CACHE_TTL_LISTAS
    # 4. retornar lista com id, nome_lista, total_itens
    pass


@listas_bp.route("/usuarios/<int:usuario_id>/listas/<int:lista_id>/itens", methods=["GET"])
def list_itens(usuario_id: int, lista_id: int):
    # TODO: implementar
    # 1. checar cache 'itens_lista:{lista_id}'
    # 2. chamar q.list_itens(conn, lista_id, usuario_id)
    # 3. armazenar no cache com TTL CACHE_TTL_LISTAS
    # 4. retornar lista de itens
    pass


@listas_bp.route("/usuarios/<int:usuario_id>/listas/<int:lista_id>/itens", methods=["POST"])
def upsert_itens(usuario_id: int, lista_id: int):
    # TODO: implementar
    # 1. validar body (array 'itens' com pelo menos um elemento)
    # 2. chamar q.upsert_itens(conn, lista_id, usuario_id, itens)
    # 3. invalidar cache 'itens_lista:{lista_id}'
    # 4. retornar itens inseridos/atualizados
    pass


@listas_bp.route("/usuarios/<int:usuario_id>/listas/<int:lista_id>/itens", methods=["DELETE"])
def delete_itens(usuario_id: int, lista_id: int):
    # TODO: implementar
    # 1. validar body (array 'nomes' com pelo menos um elemento)
    # 2. chamar q.delete_itens(conn, lista_id, usuario_id, nomes)
    # 3. invalidar cache 'itens_lista:{lista_id}'
    # 4. retornar { removidos: [...] }
    pass
