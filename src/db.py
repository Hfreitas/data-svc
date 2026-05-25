from contextlib import contextmanager

import psycopg2
from psycopg2 import pool

from src.config import Config

_pool: pool.ThreadedConnectionPool | None = None


def init_db():
    global _pool
    _pool = pool.ThreadedConnectionPool(minconn=1, maxconn=5, dsn=Config.DATABASE_URL)


@contextmanager
def get_db_conn():
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        if conn.closed:
            _pool.putconn(conn, close=True)
        else:
            try:
                conn.rollback()
            except Exception:
                pass
            _pool.putconn(conn)
        raise
    else:
        _pool.putconn(conn)
