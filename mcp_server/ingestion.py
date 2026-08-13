
import json
import requests
import feedparser
from psycopg2.extras import execute_values

import lakebase
from embeddings import _get_model

OPENALEX_URL = "https://api.openalex.org/works"
OPENALEX_MAILTO = "felixemilio9312@gmail.com"
ARXIV_URL = "http://export.arxiv.org/api/query"


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    if not inverted_index:
        return ""
    positions = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


def _parse_openalex_work(w: dict) -> tuple[dict, list[dict], list[dict]]:
    paper_id = f"openalex:{w['id'].split('/')[-1]}"
    paper = {
        "paper_id": paper_id, "source": "openalex", "source_id": w["id"].split("/")[-1],
        "title": w.get("title") or "",
        "abstract": _reconstruct_abstract(w.get("abstract_inverted_index")),
        "publication_year": w.get("publication_year"), "doi": w.get("doi"),
        "oa_url": (w.get("open_access") or {}).get("oa_url"),
        "topics": json.dumps([t["display_name"] for t in w.get("topics", [])]),
    }
    authors, paper_authors = [], []
    for a in w.get("authorships", []):
        author = a.get("author", {})
        author_id = (author.get("id") or "").split("/")[-1]
        if not author_id:
            continue
        authors.append({
            "author_id": f"openalex:{author_id}", "name": author.get("display_name", ""),
            "institution": (a.get("institutions") or [{}])[0].get("display_name"),
        })
        paper_authors.append({"paper_id": paper_id, "author_id": f"openalex:{author_id}"})
    return paper, authors, paper_authors


def _search_openalex(query: str, per_page: int = 15):
    half = max(1, per_page // 2)
    remainder = per_page - half
    papers, authors, paper_authors, seen = [], [], [], set()

    for sort, n in [("cited_by_count:desc", half), ("publication_date:desc", remainder)]:
        params = {
            "search": query, "per-page": n, "mailto": OPENALEX_MAILTO,
            "sort": sort, "filter": "has_abstract:true,is_oa:true",
        }
        resp = requests.get(OPENALEX_URL, params=params, timeout=30)
        resp.raise_for_status()
        for w in resp.json()["results"]:
            paper, p_authors, p_pa = _parse_openalex_work(w)
            if paper["paper_id"] in seen:
                continue
            seen.add(paper["paper_id"])
            papers.append(paper)
            authors.extend(p_authors)
            paper_authors.extend(p_pa)
    return papers, authors, paper_authors


def _parse_arxiv_entry(entry) -> tuple[dict, list[dict], list[dict]]:
    arxiv_id = entry.id.split("/abs/")[-1]
    paper_id = f"arxiv:{arxiv_id}"
    pdf_url = next((l.href for l in entry.links if getattr(l, "type", "") == "application/pdf"), None)
    paper = {
        "paper_id": paper_id, "source": "arxiv", "source_id": arxiv_id,
        "title": entry.title.replace("\n", " ").strip(),
        "abstract": entry.summary.replace("\n", " ").strip(),
        "publication_year": int(entry.published[:4]), "doi": getattr(entry, "arxiv_doi", None),
        "oa_url": pdf_url,
        "topics": json.dumps([t["term"] for t in entry.tags] if hasattr(entry, "tags") else []),
    }
    authors, paper_authors = [], []
    for a in entry.authors:
        author_id = f"arxiv:{a.name.replace(' ', '_')}"
        authors.append({"author_id": author_id, "name": a.name, "institution": None})
        paper_authors.append({"paper_id": paper_id, "author_id": author_id})
    return paper, authors, paper_authors


def _search_arxiv(query: str, max_results: int = 15):
    half = max(1, max_results // 2)
    remainder = max_results - half
    papers, authors, paper_authors, seen = [], [], [], set()

    for sort_by, n in [("relevance", half), ("submittedDate", remainder)]:
        params = {
            "search_query": f"(all:{query})", "sortBy": sort_by,
            "sortOrder": "descending", "max_results": n,
        }
        resp = requests.get(ARXIV_URL, params=params, timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            paper, p_authors, p_pa = _parse_arxiv_entry(entry)
            if paper["paper_id"] in seen:
                continue
            seen.add(paper["paper_id"])
            papers.append(paper)
            authors.extend(p_authors)
            paper_authors.extend(p_pa)
    return papers, authors, paper_authors


def _upsert(cur, table, rows, conflict_cols):
    if not rows:
        return
    cols = list(rows[0].keys())
    conflict = ", ".join(conflict_cols)
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in conflict_cols)
    on_conflict = f"ON CONFLICT ({conflict}) DO UPDATE SET {updates}" if updates else f"ON CONFLICT ({conflict}) DO NOTHING"
    query = f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s {on_conflict}"
    values = [tuple(r[c] for c in cols) for r in rows]
    execute_values(cur, query, values)


def ingest_and_embed(query: str, per_source: int = 15) -> int:
    oa_papers, oa_authors, oa_pa = _search_openalex(query, per_source)
    ax_papers, ax_authors, ax_pa = _search_arxiv(query, per_source)
    all_papers = oa_papers + ax_papers
    all_authors = list({a["author_id"]: a for a in (oa_authors + ax_authors)}.values())
    all_pa = oa_pa + ax_pa

    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            _upsert(cur, "papers", all_papers, ["source", "source_id"])
            _upsert(cur, "authors", all_authors, ["author_id"])
            _upsert(cur, "paper_authors", all_pa, ["paper_id", "author_id"])
        conn.commit()

    model = _get_model()
    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT paper_id, abstract FROM papers WHERE embedding IS NULL LIMIT 50")
            rows = cur.fetchall()
            candidates = [r for r in rows if r["abstract"]]
            if candidates:
                vectors = model.encode([r["abstract"] for r in candidates], show_progress_bar=False).tolist()
                for row, vec in zip(candidates, vectors):
                    cur.execute(
                        "UPDATE papers SET embedding = %s::vector WHERE paper_id = %s",
                        (json.dumps(vec), row["paper_id"]),
                    )
            conn.commit()

    return len(all_papers)