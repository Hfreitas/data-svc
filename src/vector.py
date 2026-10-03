"""Busca vetorial na Upstash Vector — backend alternativo ao pgvector.

Espelha a assinatura e o shape de `src/queries/rag.py::busca_semantica` de
propósito: a rota troca de um para o outro sem que nada a jusante (n8n, agentes)
perceba. Duas diferenças de comportamento da Upstash, medidas contra o índice
real em 2026-08-17 (A/B do F5, `meire/docs/rag-upstash-vector-plano.md`), são
neutralizadas aqui — sem elas o empate de recall 0,92 com o pgvector não se
reproduz:

1. **Escala.** A Upstash devolve `(1 + cos)/2`, não o cosseno. Mesmo chunk para
   "quando vence o DAS?": 0,421097 no pgvector, 0,710548 na Upstash. Aplicar
   `RAG_MATCH_THRESHOLD` no número cru faria o filtro aceitar tudo acima de
   cosseno -0,20 — ou seja, deixaria de filtrar.
2. **Recall aproximada.** A busca é HNSW e o feixe de exploração sai do `topK`
   pedido. Com topK<=10 a query do carnê-leão perdia o vizinho verdadeiro
   (cos 0,601) e devolvia chunks a 0,377; com topK=20 ele voltava em 1º lugar.
   Daí o over-fetch: pede muito mais e trunca aqui. Continua sendo UMA query, e
   portanto um único crédito da cota diária.

Ao contrário do `redis_cache` (fail-open, cache é volátil por definição), aqui a
falha **levanta**: devolver lista vazia seria um 200 sem fundamento, com a
Upstash parecendo saudável enquanto o agente responde do nada. Quem chama decide
o fallback — hoje, o pgvector.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from src.config import Config

_TIMEOUT = 5.0  # busca é síncrona no caminho da resposta ao usuário

FATOR_OVERFETCH = 20

# mesmo mapa de `src/routes/rag.py`: tags e namespaces usam `pl`, o Orbit manda
# `profissional_liberal`. Namespace inexistente não é erro na Upstash — devolve
# vazio —, então normalizar aqui é o que separa "sem resultado" de "sem busca".
PERFIL_PARA_NAMESPACE = {
    "profissional_liberal": "pl",
    "pl": "pl",
    "mei": "mei",
    "autonomo": "autonomo",
}


class VectorIndisponivel(Exception):
    """Busca não pôde ser feita (credencial, rede, perfil sem namespace)."""


def habilitado() -> bool:
    return bool(Config.UPSTASH_VECTOR_REST_URL and Config.UPSTASH_VECTOR_REST_TOKEN)


def para_escala_cosseno(score: float) -> float:
    """`(1+cos)/2` -> `cos`. Transformação monótona: não altera o ranking."""
    return score * 2.0 - 1.0


def busca_semantica(
    embedding: list[float], threshold: float, count: int, perfil: str | None = None
) -> list:
    """Mesmo contrato de `queries.rag.busca_semantica`, servido pela Upstash.

    `perfil` é **obrigatório** aqui, ao contrário do pgvector: lá a ausência de
    perfil significa "sem filtro, busca tudo"; aqui não existe namespace que
    contenha tudo (`comum` é expandido nos três perfis na escrita, justamente
    para nenhuma query precisar dele). Buscar no namespace default devolveria
    zero vetores — 200 vazio silencioso. Levantar deixa a decisão com a rota.
    """
    if not habilitado():
        raise VectorIndisponivel("UPSTASH_VECTOR_REST_URL/_TOKEN não configurados")

    namespace = PERFIL_PARA_NAMESPACE.get(str(perfil or "").lower().strip())
    if not namespace:
        raise VectorIndisponivel(f"perfil sem namespace correspondente: {perfil!r}")

    corpo = json.dumps(
        {
            "vector": embedding,
            "topK": count * FATOR_OVERFETCH,
            "includeData": True,      # o texto do chunk vive em `data`
            "includeMetadata": False,  # a rota não devolve metadata; poupa banda
        }
    ).encode("utf-8")

    url = Config.UPSTASH_VECTOR_REST_URL.rstrip("/") + f"/query/{namespace}"
    req = urllib.request.Request(url, data=corpo, method="POST")
    req.add_header("Authorization", f"Bearer {Config.UPSTASH_VECTOR_REST_TOKEN}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            payload = json.loads(resp.read())
    except Exception as e:  # HTTPError, URLError, timeout, JSON inválido
        raise VectorIndisponivel(f"{type(e).__name__}: {e}") from e

    resultados = [
        {
            "id": r["id"],
            "content": r.get("data") or "",
            "similarity": para_escala_cosseno(float(r["score"])),
        }
        for r in payload.get("result") or []
    ]
    return [r for r in resultados if r["similarity"] > threshold][:count]
