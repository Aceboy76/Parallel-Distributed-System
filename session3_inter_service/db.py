from __future__ import annotations
import getpass
import os
from contextlib import contextmanager
import psycopg2
from psycopg2 import pool
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

_pool: pool.SimpleConnectionPool | None = None

def init_pool(password: str | None = None, minconn: int = 1, maxconn: int = 8):
    global _pool
    if _pool is not None:
        return
    pw = password if password is not None else DB_PASSWORD
    if not pw:
        pw = getpass.getpass(f'PostgreSQL password for {DB_USER}@{DB_HOST}: ')
    _pool = pool.SimpleConnectionPool(minconn, maxconn, host=DB_HOST, port=DB_PORT,
                                      database=DB_NAME, user=DB_USER, password=pw)
    conn = _pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
    finally:
        _pool.putconn(conn)

def close_pool():
    global _pool
    if _pool is not None:
        _pool.closeall(); _pool = None

@contextmanager
def connection():
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)

def fetchall(sql: str, params=()):
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

def fetchone(sql: str, params=()):
    rows = fetchall(sql, params)
    return rows[0] if rows else None

def execute(sql: str, params=()):
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()

def table_counts():
    tables = ['student_assessment','customers','entitlements','assessment_defs','oulad_monetization']
    out = {}
    for t in tables:
        row = fetchone(f'SELECT COUNT(*) AS n FROM {t}')
        out[t] = int(row['n']) if row else 0
    return out
