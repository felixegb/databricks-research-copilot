-- Indice para busqueda semantica (HNSW, rapido para similitud coseno)
CREATE INDEX ON papers USING hnsw (embedding vector_cosine_ops);
 
-- Indices para las consultas mas comunes del agente
CREATE INDEX idx_goals_user ON learning_goals(user_id);
CREATE INDEX idx_collections_user ON collections(user_id);
CREATE INDEX idx_progress_user ON reading_progress(user_id);
CREATE INDEX idx_notes_paper ON notes(paper_id);
