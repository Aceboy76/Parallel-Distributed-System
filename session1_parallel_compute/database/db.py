from __future__ import annotations

from psycopg2 import pool

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "cma_flow_db"
DB_USER = "postgres"

_pool: pool.SimpleConnectionPool | None = None


def init_pool(password: str, minconn: int = 1, maxconn: int = 5):
    global _pool

    if _pool is not None:
        return

    _pool = pool.SimpleConnectionPool(
        minconn,
        maxconn,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=password,
    )

    conn = _pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    finally:
        _pool.putconn(conn)


def is_ready() -> bool:
    return _pool is not None


def get_conn():
    if _pool is None:
        raise RuntimeError(
            "Database pool not initialized. Call init_pool() first."
        )
    return _pool.getconn()


def put_conn(conn):
    if _pool is not None:
        _pool.putconn(conn)
