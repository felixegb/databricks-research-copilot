"""
Research Copilot MCP server.
 
Expone las herramientas del agente (Fase 4) sobre MCP para que un agente de
Agent Bricks las llame como cualquier otro tool:
    - search_papers(goal_text, top_k)
    - add_to_collection(collection_id, paper_id)
    - get_next_paper(user_id, collection_id)
 
Mismo patron que mcp_server/alpaca_mcp_server.py de day-3 (FastMCP,
transporte streamable HTTP).
 
Correr localmente:
    python research_mcp_server.py
"""
 
import json
import logging
import os
 
from fastmcp import FastMCP
 
import lakebase
from embeddings import embed_query
from ingestion import ingest_and_embed

 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("research-mcp-server")
 
mcp = FastMCP("research-copilot")
 
 
@mcp.tool
def search_papers(goal_text: str, top_k: int = 6) -> list[dict]:
    """
    Busca los papers mas relevantes semanticamente para un objetivo de
    aprendizaje o pregunta de investigacion.

    Args:
        goal_text: Descripcion del objetivo de aprendizaje o pregunta.
        top_k: Numero maximo de papers a devolver (default 6).

    Returns:
        Una lista de dicts con paper_id, title, abstract, doi, oa_url.
        Lista vacia si no hay papers suficientemente relevantes.
    """
    try:
        vec = embed_query(goal_text)
        rows = lakebase.run_query(
            "SELECT * FROM search_papers(%s::vector, %s)",
            (json.dumps(vec), top_k),
        )
        return [r for r in rows if r["distance"] <= RELEVANCE_THRESHOLD]
    except Exception as e:
        logger.exception("search_papers fallo")
        return [{"error": str(e)}]


@mcp.tool
def ingest_topic(query: str, per_source: int = 15) -> dict:
    """
    Busca e indexa papers nuevos sobre un tema que search_papers no cubre
    todavia. Usar SOLO si search_papers no devolvio resultados relevantes.

    Args:
        query: Tema o pregunta a buscar en OpenAlex/arXiv.
        per_source: Cuantos papers pedir a cada fuente (default 15).

    Returns:
        Un dict con la cantidad de
    """
    try:
        n = ingest_and_embed(query, per_source=per_source)
        return {"papers_agregados": n }
    except Exception as e:
        logger.exception("ingest_topic fallo")
        return {"error": str(e)}   
 
 
@mcp.tool
def add_to_collection(collection_id: str, paper_id: str) -> dict:
    """
    Anade un paper a una coleccion del usuario.
 
    Args:
        collection_id: UUID de la coleccion.
        paper_id: ID del paper a anadir (ej. 'arxiv:2501.12345').
 
    Returns:
        Un dict con el resultado de la operacion.
    """
    try:
        rows = lakebase.run_query(
            "SELECT add_to_collection(%s::uuid, %s) AS result",
            (collection_id, paper_id),
        )
        return rows[0] if rows else {"result": None}
    except Exception as e:
        logger.exception("add_to_collection fallo")
        return {"error": str(e)}
 
 
@mcp.tool
def get_next_paper(user_id: str, collection_id: str) -> dict:
    """
    Recomienda el siguiente paper no leido de una coleccion.
 
    Args:
        user_id: UUID del usuario.
        collection_id: UUID de la coleccion.
 
    Returns:
        Un dict con paper_id y title, o valores None si no queda nada por leer.
    """
    try:
        rows = lakebase.run_query(
            "SELECT * FROM get_next_paper(%s::uuid, %s::uuid)",
            (user_id, collection_id),
        )
        return rows[0] if rows else {"paper_id": None, "title": None}
    except Exception as e:
        logger.exception("get_next_paper fallo")
        return {"error": str(e)}
 
 
if __name__ == "__main__":
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", 8000)))
    mcp.run(transport="http", host="0.0.0.0", port=port)
