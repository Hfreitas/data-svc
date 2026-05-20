from datetime import date
from flask import Blueprint, request

from src.db import get_db_conn
from src.cache import cache_get, cache_set
from src.config import Config
from src.utils.api_response import fail, ok
import src.queries.business as q

business_bp = Blueprint("business", __name__)


@business_bp.route("/usuarios/<int:usuario_id>/contexto-business", methods=["GET"])
def get_contexto_business(usuario_id: int):
    cached = cache_get("contexto_business", str(usuario_id))
    if cached:
        return ok(200, cached)

    with get_db_conn() as conn:
        perfil = q.get_contexto_usuario(conn, usuario_id)
        if not perfil:
            return fail("usuario_nao_encontrado", status_code=404)

        semana = q.get_registros_semana(conn, usuario_id)
        mes = q.get_registros_mes(conn, usuario_id)
        historico = q.get_historico_meses(conn, usuario_id)
        fat_ano = q.get_faturamento_acumulado_ano(conn, usuario_id)
        gastos_rec = q.get_gastos_recorrentes(conn, usuario_id)

    hoje = date.today()
    dias_pt = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dia_semana = dias_pt[hoje.weekday()]
    semana_do_mes = (hoje.day - 1) // 7 + 1

    data_inicio = perfil.get("data_primeiro_contato")
    mes_uso = 0
    if data_inicio:
        d = data_inicio.date() if hasattr(data_inicio, "date") else data_inicio
        mes_uso = (hoje.year - d.year) * 12 + (hoje.month - d.month) + 1

    # primeira_segunda: true se hoje é segunda E é a primeira segunda do mês do usuário
    primeira_segunda = (
        hoje.weekday() == 0
        and data_inicio is not None
        and (hoje.year, hoje.month) == (data_inicio.year, data_inicio.month)
    ) if data_inicio else False

    payload = {
        "perfil": {
            "nome_mei": perfil.get("nome") or "",
            "nome_negocio": perfil.get("razao_social") or "",
            "cluster": perfil.get("tipo_negocio") or "",
            "tipo_negocio": perfil.get("tipo_negocio") or "",
            "descricao_negocio": perfil.get("descricao_negocio") or "",
            "descricao_completa": bool(perfil.get("descricao_completa")),
        },
        "flags": {
            "primeira_segunda": primeira_segunda,
            "primeiro_relatorio": perfil.get("ultimo_relatorio") is None,
            "mes_uso": mes_uso,
            "status_trial": perfil.get("status_trial", "trial"),
            "confirmacao_lembretes": bool(perfil.get("confirmacao_lembretes")),
            "proximo_campo_fila": perfil.get("proximo_campo_fila"),
        },
        "data_context": {
            "data_atual": hoje.strftime("%d/%m/%Y"),
            "dia_semana": dia_semana,
            "semana_do_mes": semana_do_mes,
            "data_inicio_meirelles": data_inicio.strftime("%Y-%m-%d") if data_inicio else None,
        },
        "financeiro": {
            "registros_semana": semana,
            "registros_mes": mes,
            "historico_meses": historico,
            "faturamento_acumulado_ano": fat_ano,
            "gastos_recorrentes": gastos_rec,
            "ultimo_relatorio": perfil["ultimo_relatorio"].isoformat() if perfil.get("ultimo_relatorio") else None,
        },
    }

    cache_set("contexto_business", str(usuario_id), payload, Config.CACHE_TTL_CONTEXTO_BUSINESS)
    return ok(200, payload)


@business_bp.route("/usuarios/<int:usuario_id>/meicheck-logs", methods=["POST"])
def post_meicheck_log(usuario_id: int):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    body["usuario_id"] = body.get("usuario_id") or str(usuario_id)

    with get_db_conn() as conn:
        log = q.insert_meicheck_log(conn, body)
        return ok(201, log)
