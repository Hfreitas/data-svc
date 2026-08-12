import hashlib

from flask import Blueprint, request
from openai import OpenAI
from src.db import get_db_conn
from src import redis_cache
from src.config import Config
from src.utils.api_response import ok, fail
import src.queries.rag as queries

rag_bp = Blueprint("rag", __name__)
_openai_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        # Embeddings always hit OpenAI directly — no base_url override (Gemini compat doesn't support embeddings)
        _openai_client = OpenAI(api_key=Config.EMBEDDINGS_API_KEY)
    return _openai_client


@rag_bp.post("/rag/busca")
def busca_rag():
    body = request.get_json()
    if not body or "pergunta" not in body:
        return fail("missing_field", "Campo obrigatório: pergunta", 400)

    pergunta = body["pergunta"]
    match_count = int(body.get("match_count", Config.RAG_MATCH_COUNT))
    match_threshold = float(body.get("match_threshold", Config.RAG_MATCH_THRESHOLD))

    # Cache por hash da query normalizada + params: corta custo OpenAI embeddings + latência
    cache_key = "rag:" + hashlib.sha256(
        f"{pergunta.strip().lower()}|{match_count}|{match_threshold}".encode("utf-8")
    ).hexdigest()
    cached = redis_cache.cache_get(cache_key)
    if cached is not None:
        return ok(200, {"resultados": cached})

    try:
        resp = _get_client().embeddings.create(
            input=pergunta, model=Config.EMBEDDING_MODEL
        )
        embedding = resp.data[0].embedding
    except Exception as e:
        return fail("embedding_error", str(e), 500)

    with get_db_conn() as conn:
        resultados = queries.busca_semantica(conn, embedding, match_threshold, match_count)

    redis_cache.cache_set(cache_key, resultados, Config.REDIS_TTL_RAG)
    return ok(200, {"resultados": resultados})
