import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL: str = os.environ["DATABASE_URL"]
    PORT: int = int(os.getenv("PORT", 5000))
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")

    API_KEY: str | None = (os.getenv("API_KEY") or "").strip() or None   # None = auth desativada (dev local)

    # Cache TTLs (segundos)
    CACHE_TTL_USUARIO: int = int(os.getenv("CACHE_TTL_USUARIO", 60))
    CACHE_TTL_SALDO: int = int(os.getenv("CACHE_TTL_SALDO", 300))
    CACHE_TTL_COMPROVANTES: int = int(os.getenv("CACHE_TTL_COMPROVANTES", 300))
    CACHE_TTL_AGENDAMENTOS: int = int(os.getenv("CACHE_TTL_AGENDAMENTOS", 120))
    CACHE_TTL_LISTAS: int = int(os.getenv("CACHE_TTL_LISTAS", 300))
    CACHE_TTL_FEEDBACKS: int = int(os.getenv("CACHE_TTL_FEEDBACKS", 300))
    CACHE_TTL_CONTEXTO_BUSINESS: int = int(os.getenv("CACHE_TTL_CONTEXTO_BUSINESS", 60))

    # Cache L2 distribuído (Upstash Redis REST) — não-fatal, Postgres é fonte da verdade.
    # Vazio = desativado (wrapper vira no-op). Uma DB free serve STG+PRD via prefixo.
    UPSTASH_REDIS_REST_URL: str = (os.getenv("UPSTASH_REDIS_REST_URL") or "").strip()
    UPSTASH_REDIS_REST_TOKEN: str = (os.getenv("UPSTASH_REDIS_REST_TOKEN") or "").strip()
    CACHE_ENV_PREFIX: str = (os.getenv("CACHE_ENV_PREFIX") or "").strip()  # ex: "stg" / "prd"
    REDIS_TTL_USER: int = int(os.getenv("REDIS_TTL_USER", 600))        # contexto usuário (curto; DB é lei)
    REDIS_TTL_RAG: int = int(os.getenv("REDIS_TTL_RAG", 3600))         # resultado busca vetorial
    REDIS_TTL_MEMORIA: int = int(os.getenv("REDIS_TTL_MEMORIA", 43200))  # janela quente chat (12h)
    DEDUP_TTL: int = int(os.getenv("DEDUP_TTL", 60))                   # janela de deduplicação
    RATE_LIMIT_MAX: int = int(os.getenv("RATE_LIMIT_MAX", 30))         # requests por janela
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", 60))   # janela do rate-limit (s)

    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.environ.get("OPENAI_BASE_URL", "")
    # Embeddings always via OpenAI (1536 dims fixed in DB). Falls back to OPENAI_API_KEY if not set.
    EMBEDDINGS_API_KEY: str = os.environ.get("EMBEDDINGS_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    RAG_MATCH_THRESHOLD: float = float(os.environ.get("RAG_MATCH_THRESHOLD", "0.7"))
    RAG_MATCH_COUNT: int = int(os.environ.get("RAG_MATCH_COUNT", "5"))

    @classmethod
    def validate(cls) -> None:
        if cls.FLASK_ENV == "production" and cls.API_KEY is None:
            raise EnvironmentError(
                "API_KEY é obrigatória. "
            )


Config.validate()
