import os
 
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from databricks.sdk import WorkspaceClient
 
w = WorkspaceClient()


def _get_default_lakebase_config():
    """Obtiene la configuración de Lakebase desde el proyecto research-copilot si no hay variables de entorno."""
    project_id = "research-copilot"
    branches = list(w.postgres.list_branches(parent=f"projects/{project_id}"))
    if not branches:
        raise ValueError(f"No se encontraron branches en el proyecto {project_id}")
    
    production_branch = branches[0]  # Usar el primer branch (production)
    endpoints = list(w.postgres.list_endpoints(parent=production_branch.name))
    if not endpoints:
        raise ValueError(f"No se encontraron endpoints en {production_branch.name}")
    
    endpoint = endpoints[0]  # Usar el primer endpoint (primary)
    host = endpoint.status.hosts.host if endpoint.status and endpoint.status.hosts else None
    if not host:
        raise ValueError(f"No se pudo obtener el host del endpoint {endpoint.name}")
    
    return {
        "host": host,
        "endpoint": endpoint.name,
    }

# Configurar variables de Lakebase
# Si no existen variables de entorno, obtener configuración automáticamente
if "LAKEBASE_HOST" not in os.environ or "LAKEBASE_ENDPOINT" not in os.environ:
    _config = _get_default_lakebase_config()
    LAKEBASE_HOST = os.environ.get("LAKEBASE_HOST", _config["host"])
    LAKEBASE_ENDPOINT = os.environ.get("LAKEBASE_ENDPOINT", _config["endpoint"])
else:
    LAKEBASE_HOST = os.environ["LAKEBASE_HOST"]
    LAKEBASE_ENDPOINT = os.environ["LAKEBASE_ENDPOINT"]

LAKEBASE_PORT = os.environ.get("LAKEBASE_PORT", "5432")
LAKEBASE_DB = os.environ.get("LAKEBASE_DB", "databricks_postgres")

# El rol de Postgres para OAuth es tu identidad de Databricks (email), NO el
# nombre del perfil de la CLI. Se resuelve solo salvo que LAKEBASE_USER este seteado.
LAKEBASE_USER = os.environ.get("LAKEBASE_USER") or w.current_user.me().user_name
 
 
def get_connection():
    """Abre una conexion a Lakebase con un token OAuth efimero (sin password estatico)."""
    token = w.postgres.generate_database_credential(endpoint=LAKEBASE_ENDPOINT).token
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        dbname=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=token,
        sslmode="require",
        cursor_factory=RealDictCursor,
    )
 
 
def upsert_rows(table: str, rows: list[dict], conflict_cols: list[str]):
    """Inserta filas con upsert generico (ON CONFLICT DO UPDATE o DO NOTHING)."""
    if not rows:
        return
    cols = list(rows[0].keys())
    conflict = ", ".join(conflict_cols)
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in conflict_cols)
    
    # Si todas las columnas son de conflicto, usar DO NOTHING en lugar de DO UPDATE SET
    if updates:
        on_conflict_clause = f"ON CONFLICT ({conflict}) DO UPDATE SET {updates}"
    else:
        on_conflict_clause = f"ON CONFLICT ({conflict}) DO NOTHING"
    
    query = f"""
        INSERT INTO {table} ({", ".join(cols)})
        VALUES %s
        {on_conflict_clause}
    """
    values = [tuple(r[c] for c in cols) for r in rows]
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, query, values)
        conn.commit()
