from contextlib import contextmanager

import psycopg2
from psycopg2 import pool

from src.config import Config

_pool: pool.ThreadedConnectionPool | None = None


def init_db():
    global _pool
    # TODO: ajustar minconn/maxconn conforme carga esperada no VPS
    _pool = pool.ThreadedConnectionPool(minconn=1, maxconn=5, dsn=Config.DATABASE_URL)


@contextmanager
def get_db_conn():
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
