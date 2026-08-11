from flask import Blueprint, request, jsonify

from src.db import get_db_conn
from src.cache import cache_get, cache_set, cache_invalidate
from src.config import Config
from src.utils.validators import validate_telefone, require_fields, validate_usuario_agenda_fields
import src.queries.usuarios as q
from src.utils.api_response import fail, ok

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.route("/usuarios", methods=["GET"])
def get_usuario():
    telefone = validate_telefone(request.args.get('telefone')) 
      
    cached = cache_get("usuario", telefone)
    
    if cached:
        return jsonify(cached)
    
    with get_db_conn() as conn:
        usuario = q.find_by_telefone(conn, telefone)
        
        if not usuario:
            return fail("usuario_nao_encontrado", status_code=404)
        
        cache_set("usuario", telefone, usuario, Config.CACHE_TTL_USUARIO)
        return ok(200, usuario)



@usuarios_bp.route("/usuarios", methods=["POST"])
def create_usuario():
    body = request.get_json()
    
    require_fields(body, "numero_telefone")

    numero_telefone = body["numero_telefone"]
    validate_telefone(numero_telefone)

    with get_db_conn() as conn:
        usuario = q.upsert(conn, numero_telefone, body.get("nome"), body.get("razao_social"))
        
        cache_invalidate("usuario", numero_telefone)
        
        return ok(200, usuario)


@usuarios_bp.route("/usuarios/<int:usuario_id>", methods=["PUT"])
def update_usuario(usuario_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    allowed_fields = {
        "nome", "razao_social", "estado_atual", "interacao_previa",
        "tipo_negocio", "descricao_negocio", "descricao_objetivo",
        "area_ajuda", "preco_referencia", "dias_trabalho",
        "horario_inicio", "horario_fim",
        "versao_agente", "onboarding_step",
        "contas_fixas_completo", "onboarding_concluido", "onboarding_timestamp", "cluster",
        "confirmacao_lembretes", "cpf_cnpj",
        "perfil_tipo", "eh_mei", "profissao", "modalidade",
        "conselho_sigla", "conselho_uf", "conselho_numero",
        "uf", "municipio", "followup_agendado", "followup_timestamp",
    }

    # Validar campos de agenda primeiro para coerção de tipos
    validated = validate_usuario_agenda_fields(body)
    body.update(validated)

    fields_to_update = {
        k: v for k, v in body.items()
        if k in allowed_fields and v is not None
    }
    
    if not fields_to_update:
        return fail(
            "campos_invalidos",
            "informe ao menos um campo permitido",
            400,
        )
    
    with get_db_conn() as conn:
               
        usuario = q.update(conn, usuario_id, fields_to_update)
        if not usuario:
            return fail("usuario_nao_encontrado", status_code=404)

        cache_invalidate("usuario", usuario["numero_telefone"])
        cache_invalidate("usuario", f"id:{usuario_id}")

        return ok(200, usuario)


@usuarios_bp.route("/usuarios/<int:usuario_id>/resetar-demo", methods=["POST"])
def resetar_demo(usuario_id: int):
    with get_db_conn() as conn:
        usuario = q.reset_demo(conn, usuario_id)
        if not usuario:
            return fail("usuario_nao_encontrado", status_code=404)

        cache_invalidate("usuario", usuario["numero_telefone"])
        cache_invalidate("usuario", f"id:{usuario_id}")

        return ok(200, usuario)


@usuarios_bp.route("/usuarios/<int:usuario_id>/notificacoes", methods=["GET"])
def get_notificacoes(usuario_id: int):
    with get_db_conn() as conn:
        prefs = q.get_notificacoes(conn, usuario_id)
    return ok(200, prefs)


@usuarios_bp.route("/usuarios/<int:usuario_id>/notificacoes", methods=["PUT"])
def update_notificacoes(usuario_id: int):
    """Upsert de preferências de notificação.

    Body: objeto plano {tipo: bool}, ex: {"das": true, "inss": false}.
    Só tipos válidos (NOTIF_TIPOS) são aceitos; qualquer chave desconhecida
    rejeita a requisição inteira.
    """
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not body:
        return fail("body_invalido", "informe {tipo: bool}", 400)

    invalidos = [k for k in body if k not in q.NOTIF_TIPOS]
    if invalidos:
        return fail(
            "tipo_invalido",
            f"tipos não permitidos: {', '.join(invalidos)}",
            400,
        )

    prefs = {k: bool(v) for k, v in body.items()}

    with get_db_conn() as conn:
        atual = q.upsert_notificacoes(conn, usuario_id, prefs)
    return ok(200, atual)


@usuarios_bp.route("/usuarios/<int:usuario_id>/prox-nfe", methods=["GET"])
def prox_nfe(usuario_id: int):
    with get_db_conn() as conn:
        result = q.get_prox_nfe(conn, usuario_id)
    return ok(200, result)


@usuarios_bp.route("/usuarios/<int:usuario_id>/clientes-nf", methods=["GET"])
def get_clientes_nf(usuario_id: int):
    with get_db_conn() as conn:
        clientes = q.get_clientes_nf(conn, usuario_id)
    return ok(200, clientes)


@usuarios_bp.route("/usuarios/<int:usuario_id>/clientes-nf", methods=["POST"])
def create_cliente_nf(usuario_id: int):
    body = request.get_json(silent=True)
    if not body or not body.get("nome") or not body.get("cnpj"):
        return fail("dados_incompletos", "Campos obrigatorios: nome, cnpj", 400)

    with get_db_conn() as conn:
        cliente = q.save_cliente_nf(
            conn,
            usuario_id,
            body["nome"],
            body["cnpj"],
            body.get("email", ""),
        )
    return ok(200, cliente)

