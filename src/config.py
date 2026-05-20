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
