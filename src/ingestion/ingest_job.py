import json
from src.db.connection import upsert_rows
from src.ingestion.openalex_client import search_works
from src.ingestion.arxiv_client import search_arxiv
 
def _prep_papers(papers: list[dict]) -> list[dict]:
    for p in papers:
        p["topics"] = json.dumps(p.get("topics") or [])
    return papers
 
def ingest_for_query(query: str, per_source: int = 25):
    oa_papers, oa_authors, oa_pa = search_works(query, per_page=per_source)
    ax_papers, ax_authors, ax_pa = search_arxiv(query, max_results=per_source)
 
    all_papers = _prep_papers(oa_papers + ax_papers)
    all_authors = {a["author_id"]: a for a in (oa_authors + ax_authors)}.values()
    all_pa = oa_pa + ax_pa
 
    upsert_rows("papers", all_papers, conflict_cols=["source", "source_id"])
    upsert_rows("authors", list(all_authors), conflict_cols=["author_id"])
    upsert_rows("paper_authors", all_pa, conflict_cols=["paper_id", "author_id"])
 
    print(f"Ingeridos {len(all_papers)} papers para '{query}'")
 
if __name__ == "__main__":
    ingest_for_query("retrieval augmented generation", per_source=20)
