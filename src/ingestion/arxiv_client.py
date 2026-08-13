import feedparser
import requests
 
BASE_URL = "http://export.arxiv.org/api/query"
 
def search_arxiv(query: str, max_results: int = 25) -> tuple[list, list, list]:
    params = {
        "search_query": f"(all:{query})",
        "sortBy": "relevance",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.text)
 
    papers, authors, paper_authors = [], [], []
    for entry in feed.entries:
        arxiv_id = entry.id.split("/abs/")[-1]
        paper_id = f"arxiv:{arxiv_id}"
        pdf_url = next(
            (l.href for l in entry.links if getattr(l, "type", "") == "application/pdf"),
            None,
        )
        papers.append({
            "paper_id": paper_id,
            "source": "arxiv",
            "source_id": arxiv_id,
            "title": entry.title.replace("\n", " ").strip(),
            "abstract": entry.summary.replace("\n", " ").strip(),
            "publication_year": int(entry.published[:4]),
            "doi": getattr(entry, "arxiv_doi", None),
            "oa_url": pdf_url,
            "topics": [t["term"] for t in entry.tags] if hasattr(entry, "tags") else [],
        })
        for a in entry.authors:
            author_id = f"arxiv:{a.name.replace(' ', '_')}"
            authors.append({"author_id": author_id, "name": a.name, "institution": None})
            paper_authors.append({"paper_id": paper_id, "author_id": author_id})
    return papers, authors, paper_authors
