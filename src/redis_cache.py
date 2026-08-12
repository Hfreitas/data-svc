"""Cache L2 distribuído sobre a REST API do Upstash Redis.

Invariantes (Fase 6 do plano Orbit):
- Postgres é a fonte da verdade. Este cache é volátil e **não-fatal**: qualquer
  falha (rede, 5xx, timeout, credencial ausente) degrada para miss/None e o
  caller cai no Postgres. Nenhum estado de FSM deriva daqui.
- Stateless: usa a REST API do Upstash (sem processo/conexão persistente na VPS),
  então o padrão de pool morto do psycopg2 não se aplica.
- Sem dependência nova: usa `urllib` da stdlib (mantém a VPS 1vCPU/4GB leve).

Chaves recebem prefixo de ambiente (`stg:` / `prd:`) para compartilhar uma DB
Upstash free entre STG e PRD sem colisão.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from src.config import Config

# Timeout curto: um Redis lento nunca deve estagnar um request (fail-open).
_TIMEOUT = 1.5


def _enabled() -> bool:
    return bool(Config.UPSTASH_REDIS_REST_URL and Config.UPSTASH_REDIS_REST_TOKEN)


def _key(key: str) -> str:
    prefix = Config.CACHE_ENV_PREFIX
    return f"{prefix}:{key}" if prefix else key


def _command(args: list) -> object | None:
    """Executa um comando Redis via REST (body = array JSON).

    Retorna o campo `result` da resposta Upstash, ou None em qualquer falha.
    Nunca levanta exceção — o cache é sempre não-fatal.
    """
    if not _enabled():
        return None
    try:
        body = json.dumps(args).encode("utf-8")
        req = urllib.request.Request(
            Config.UPSTASH_REDIS_REST_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {Config.UPSTASH_REDIS_REST_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if isinstance(payload, dict) and "error" in payload:
            return None
        return payload.get("result") if isinstance(payload, dict) else None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def cache_get(key: str):
    """GET desserializado (JSON) ou None em miss/erro."""
    raw = _command(["GET", _key(key)])
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw


def cache_set(key: str, val, ex: int) -> bool:
    """SET com expiração (segundos). True se gravou."""
    payload = json.dumps(val, default=str)
    return _command(["SET", _key(key), payload, "EX", str(ex)]) == "OK"


def cache_del(key: str) -> bool:
    """DEL. True se removeu ao menos uma chave."""
    res = _command(["DEL", _key(key)])
    return bool(res)


def cache_setnx(key: str, val, ex: int) -> bool:
    """SET ... NX EX — grava só se ausente. True se **adquiriu** (não existia)."""
    payload = json.dumps(val, default=str)
    return _command(["SET", _key(key), payload, "EX", str(ex), "NX"]) == "OK"


def cache_incr(key: str, ex: int) -> int | None:
    """INCR; no 1º incremento aplica EXPIRE (janela deslizante por chave nova).

    Retorna o contador atual, ou None em erro (fail-open — sem bloqueio).
    """
    res = _command(["INCR", _key(key)])
    if res is None:
        return None
    try:
        count = int(res)
    except (ValueError, TypeError):
        return None
    if count == 1:
        _command(["EXPIRE", _key(key), str(ex)])
    return count


# --- Guardas de alto nível (dedup / rate-limit) -------------------------------

def dedup_is_duplicate(telefone: str, msg_hash: str, ex: int | None = None) -> bool:
    """True se esta (telefone, msg) já foi vista dentro da janela.

    Usa SETNX: a 1ª ocorrência adquire a chave (retorna False = processa);
    repetições dentro da janela falham o NX (retorna True = ignora duplicata).
    Fail-open: se o cache estiver indisponível, nunca marca como duplicata.
    """
    ttl = ex if ex is not None else Config.DEDUP_TTL
    acquired = cache_setnx(f"dedup:{telefone}:{msg_hash}", 1, ttl)
    return not acquired if _enabled() else False


def rate_limit_exceeded(telefone: str, limit: int | None = None, ex: int | None = None) -> bool:
    """True se o telefone excedeu `limit` requests na janela `ex`.

    Fail-open: contador None (cache down) nunca bloqueia.
    """
    max_hits = limit if limit is not None else Config.RATE_LIMIT_MAX
    window = ex if ex is not None else Config.RATE_LIMIT_WINDOW
    count = cache_incr(f"rl:{telefone}", window)
    return count is not None and count > max_hits
