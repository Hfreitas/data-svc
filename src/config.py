import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL: str = os.environ["DATABASE_URL"]
    PORT: int = int(os.getenv("PORT", 5000))
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")

    API_KEY: str | None = os.getenv("API_KEY")  # None = auth desativada (dev local)

    # Cache TTLs (segundos)
    CACHE_TTL_USUARIO: int = int(os.getenv("CACHE_TTL_USUARIO", 60))
    CACHE_TTL_SALDO: int = int(os.getenv("CACHE_TTL_SALDO", 300))
    CACHE_TTL_COMPROVANTES: int = int(os.getenv("CACHE_TTL_COMPROVANTES", 300))
    CACHE_TTL_AGENDAMENTOS: int = int(os.getenv("CACHE_TTL_AGENDAMENTOS", 120))
    CACHE_TTL_LISTAS: int = int(os.getenv("CACHE_TTL_LISTAS", 300))
