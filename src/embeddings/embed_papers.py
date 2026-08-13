import json
import os
from sentence_transformers import SentenceTransformer
from src.db.connection import get_connection
 
EMBEDDING_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
)
 
# Mismo mapeo que day-2/notebooks/ingest_ticker_news_embeddings.py:
# cada modelo emite un tamano de vector distinto y VECTOR(N) debe coincidir exactamente.
match EMBEDDING_MODEL_NAME:
    case "sentence-transformers/all-MiniLM-L6-v2":
        EMBEDDING_DIM = 384
    case "sentence-transformers/all-mpnet-base-v2":
        EMBEDDING_DIM = 768
    case "BAAI/bge-large-en-v1.5":
        EMBEDDING_DIM = 1024
    case _:
        raise ValueError(
            f"Modelo desconocido {EMBEDDING_MODEL_NAME!r} -- agrega su dimension al match/case."
        )
 
_model: SentenceTransformer | None = None
 
 
def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model
 
def embed_query(text: str) -> list[float]:
    """Embebe un texto suelto (ej. la pregunta del usuario) con el mismo modelo que los papers."""
    model = _get_model()
    return model.encode([text], show_progress_bar=False)[0].tolist()


def embed_pending_papers(batch_size: int = 20):
    model = _get_model()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT paper_id, abstract FROM papers WHERE embedding IS NULL LIMIT %s",
                (batch_size,),
            )
            rows = cur.fetchall()
            candidates = [r for r in rows if r["abstract"]]
            if candidates:
                texts = [r["abstract"] for r in candidates]
                vectors = model.encode(texts, show_progress_bar=False).tolist()
                for row, vec in zip(candidates, vectors):
                    cur.execute(
                        "UPDATE papers SET embedding = %s::vector WHERE paper_id = %s",
                        (json.dumps(vec), row["paper_id"]),
                    )
            conn.commit()
    print(f"Embebidos {len(candidates)} papers (de {len(rows)} candidatos sin embedding)")
 
 
if __name__ == "__main__":
    embed_pending_papers()
