"""Invalidação de cache disparada de fora do processo.

Todo write que passa pelo data-svc já invalida os dois níveis (ver
`routes/usuarios.py`). O buraco é o write que NÃO passa: SQL manual, reset em
lote (Fase R), job externo. Nesses casos o L1 (TTLCache in-process) e o L2
(Upstash) seguem servindo o valor velho até o TTL — até 600s.

Isso importa mais do que "dado desatualizado": `usuarios.estado_atual` é o campo
de FSM que o Orbit lê para rotear. Stale aqui não entrega dado velho, entrega
roteamento errado do turno seguinte.

Escopo deliberado: só a entidade `usuario`. É a única com os dois níveis ligados
e a única com escritor externo medido. Namespaces L1-only (listas, saldo,
agendamentos, feedbacks) têm TTL curto e nenhum escritor fora do data-svc —
generalizar agora seria API para um problema que não existe.
"""
from flask import Blueprint, request

from src.db import get_db_conn
from src.cache import cache_invalidate
from src import redis_cache
from src.utils.validators import validate_telefone
import src.queries.usuarios as q
from src.utils.api_response import fail, ok

cache_bp = Blueprint("cache", __name__)

# Teto de lote: a Fase R foram 135 usuários, então 500 cobre o caso real com
# folga. O limite existe para o `usuario_ids`, que vira um `id = ANY(...)`.
MAX_LOTE = 500


def _parse_ids(brutos: list) -> list[int] | None:
    """Converte os ids para int. Retorna None se algum não for inteiro.

    `isinstance(True, int)` é True em Python — sem a checagem de bool, um
    `[true]` no JSON viraria o id 1 e invalidaria o usuário errado.
    """
    ids = []
    for bruto in brutos:
        if isinstance(bruto, bool):
            return None
        try:
            ids.append(int(bruto))
        except (TypeError, ValueError):
            return None
    return ids


@cache_bp.route("/cache/invalidate", methods=["POST"])
def invalidate():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return fail("body_invalido", "JSON inválido ou ausente", 400)

    telefones_brutos = body.get("telefones", [])
    ids_brutos = body.get("usuario_ids", [])

    if not isinstance(telefones_brutos, list) or not isinstance(ids_brutos, list):
        return fail("campo_invalido", "'telefones' e 'usuario_ids' devem ser listas", 400)

    if not telefones_brutos and not ids_brutos:
        return fail("campos_invalidos", "informe 'telefones' ou 'usuario_ids'", 400)

    if len(telefones_brutos) + len(ids_brutos) > MAX_LOTE:
        return fail("lote_grande", f"máximo {MAX_LOTE} alvos por chamada", 400)

    telefones = [validate_telefone(t) for t in telefones_brutos]  # aborta 400

    ids = _parse_ids(ids_brutos)
    if ids is None:
        return fail("campo_invalido", "'usuario_ids' deve conter inteiros", 400)

    nao_encontrados = []
    if ids:
        with get_db_conn() as conn:
            mapa = q.find_telefones_by_ids(conn, ids)

        nao_encontrados = [uid for uid in ids if uid not in mapa]

        for uid, telefone in mapa.items():
            # `usuarios.py` grava L1 sob duas chaves (`<tel>` e `id:<id>`).
            # Derrubar só uma deixaria a outra servindo o valor velho.
            cache_invalidate("usuario", f"id:{uid}")
            telefones.append(telefone)

    # dict.fromkeys dedupa preservando ordem: um id que resolve para um telefone
    # já informado não deve contar (nem apagar) duas vezes.
    unicos = list(dict.fromkeys(telefones))

    for telefone in unicos:
        cache_invalidate("usuario", telefone)
        # cache_del é fail-open: L2 fora do ar devolve False e não vira erro —
        # o L1 já caiu e o Postgres continua sendo a fonte da verdade.
        redis_cache.cache_del(f"user:{telefone}")

    return ok(200, {
        "invalidados": len(unicos),
        "telefones": unicos,
        "nao_encontrados": nao_encontrados,
    })
