from contextlib import contextmanager

import psycopg2
from psycopg2 import pool

from src.config import Config

_pool: pool.ThreadedConnectionPool | None = None
_POOL_MAXCONN = 5


def init_db():
    global _pool
    _pool = pool.ThreadedConnectionPool(minconn=1, maxconn=_POOL_MAXCONN, dsn=Config.DATABASE_URL)


def _get_healthy_conn():
    # Postgres/pooler pode derrubar conexões ociosas; ThreadedConnectionPool não
    # detecta isso sozinho e entrega a conexão morta no próximo getconn().
    for _ in range(_POOL_MAXCONN):
        conn = _pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return conn
        except psycopg2.OperationalError:
            _pool.putconn(conn, close=True)
    raise psycopg2.OperationalError("Não foi possível obter conexão saudável do pool de banco de dados")


@contextmanager
def get_db_conn():
    conn = _get_healthy_conn()
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
