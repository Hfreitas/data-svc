from flask import Blueprint, request
from openai import OpenAI
from src.db import get_db_conn
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

    try:
        resp = _get_client().embeddings.create(
            input=pergunta, model=Config.EMBEDDING_MODEL
        )
        embedding = resp.data[0].embedding
    except Exception as e:
        return fail("embedding_error", str(e), 500)

    with get_db_conn() as conn:
        resultados = queries.busca_semantica(conn, embedding, match_threshold, match_count)

    return ok(200, {"resultados": resultados})
