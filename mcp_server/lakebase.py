import os
from contextlib import contextmanager
 
import psycopg2
from databricks.sdk import WorkspaceClient
from psycopg2.extras import RealDictCursor
 
w = WorkspaceClient()
 
PGHOST = os.environ["PGHOST"]
PGPORT = os.environ.get("PGPORT", "5432")
PGDATABASE = os.environ["PGDATABASE"]
PGUSER = os.environ["PGUSER"]
LAKEBASE_ENDPOINT = os.environ["LAKEBASE_ENDPOINT"]
 
 
@contextmanager
def get_connection():
    token = w.postgres.generate_database_credential(endpoint=LAKEBASE_ENDPOINT).token
    conn = psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=token,
        sslmode="require",
        cursor_factory=RealDictCursor,
    )
    try:
        yield conn
    finally:
        conn.close()
 
 
def run_query(sql: str, params=None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
 
 
def run_write(sql: str, params=None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount
