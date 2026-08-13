import requests
 
BASE_URL = "https://api.openalex.org/works"
MAILTO = "felixemilio9312@gmail.com"  # mejora tu cuota (polite pool)
 
def reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex entrega el abstract como indice invertido; hay que reconstruirlo."""
    if not inverted_index:
        return ""
    positions = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))
 
def search_works(query: str, per_page: int = 25, only_oa: bool = True) -> list[dict]:
    params = {
        "search": query,
        "per-page": per_page,
        "mailto": MAILTO,
        "sort": "cited_by_count:desc",
    }
    if only_oa:
        params["filter"] = "has_abstract:true,is_oa:true"
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    results = resp.json()["results"]
 
    papers, authors, paper_authors = [], [], []
    for w in results:
        paper_id = f"openalex:{w['id'].split('/')[-1]}"
        papers.append({
            "paper_id": paper_id,
            "source": "openalex",
            "source_id": w["id"].split("/")[-1],
            "title": w.get("title") or "",
            "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
            "publication_year": w.get("publication_year"),
            "doi": w.get("doi"),
            "oa_url": (w.get("open_access") or {}).get("oa_url"),
            "topics": [t["display_name"] for t in w.get("topics", [])],
        })
        for a in w.get("authorships", []):
            author = a.get("author", {})
            author_id = (author.get("id") or "").split("/")[-1]
            if not author_id:
                continue
            authors.append({
                "author_id": f"openalex:{author_id}",
                "name": author.get("display_name", ""),
                "institution": (a.get("institutions") or [{}])[0].get("display_name"),
            })
            paper_authors.append({
                "paper_id": paper_id,
                "author_id": f"openalex:{author_id}",
            })
    return papers, authors, paper_authors
