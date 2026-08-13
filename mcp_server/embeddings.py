from sentence_transformers import SentenceTransformer
 
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
 
_model: SentenceTransformer | None = None
 
 
def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model
 
 
def embed_query(text: str) -> list[float]:
    return _get_model().encode([text], show_progress_bar=False)[0].tolist()

