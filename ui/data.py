import streamlit as st
from lakebase import run_query, run_write

DEFAULT_EMAIL = "felixemilio9312@gmail.com"


def get_current_email() -> str:
    email = st.context.headers.get("x-forwarded-email")
    return email or DEFAULT_EMAIL


def get_or_create_user(email: str) -> str:
    rows = run_query("SELECT user_id FROM users WHERE email = %s", (email,))
    if rows:
        return str(rows[0]["user_id"])
    rows = run_query(
        "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING user_id",
        (email.split("@")[0], email),
    )
    return str(rows[0]["user_id"])


def list_collections(user_id: str):
    return run_query(
        """
        SELECT c.collection_id, c.name, c.created_at, count(cp.paper_id) AS n_papers
        FROM collections c
        LEFT JOIN collection_papers cp ON cp.collection_id = c.collection_id
        WHERE c.user_id = %s
        GROUP BY c.collection_id, c.name, c.created_at
        ORDER BY c.created_at DESC
        """,
        (user_id,),
    )


def create_collection(user_id: str, name: str) -> str:
    rows = run_query(
        "INSERT INTO collections (user_id, name) VALUES (%s, %s) RETURNING collection_id",
        (user_id, name),
    )
    return str(rows[0]["collection_id"])


def list_collection_papers(collection_id: str, user_id: str):
    return run_query(
        """
        SELECT p.paper_id, p.title, p.doi, p.oa_url, p.publication_year, cp.added_at,
               COALESCE(rp.status, 'not_started') AS status
        FROM collection_papers cp
        JOIN papers p ON p.paper_id = cp.paper_id
        LEFT JOIN reading_progress rp ON rp.paper_id = p.paper_id AND rp.user_id = %s
        WHERE cp.collection_id = %s
        ORDER BY cp.added_at DESC
        """,
        (user_id, collection_id),
    )


def remove_paper_from_collection(collection_id: str, paper_id: str):
    run_write(
        "DELETE FROM collection_papers WHERE collection_id = %s AND paper_id = %s",
        (collection_id, paper_id),
    )


def search_papers_by_title(query: str, limit: int = 15):
    return run_query(
        """
        SELECT paper_id, title, publication_year FROM papers
        WHERE title ILIKE %s ORDER BY publication_year DESC NULLS LAST LIMIT %s
        """,
        (f"%{query}%", limit),
    )


def add_paper_to_collection(collection_id: str, paper_id: str):
    run_write(
        "INSERT INTO collection_papers (collection_id, paper_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (collection_id, paper_id),
    )


def list_progress(user_id: str):
    return run_query(
        """
        SELECT rp.paper_id, p.title, rp.status, rp.updated_at
        FROM reading_progress rp
        JOIN papers p ON p.paper_id = rp.paper_id
        WHERE rp.user_id = %s
        ORDER BY rp.updated_at DESC
        """,
        (user_id,),
    )


def set_progress(user_id: str, paper_id: str, status: str):
    run_write(
        """
        INSERT INTO reading_progress (user_id, paper_id, status, updated_at)
        VALUES (%s, %s, %s, now())
        ON CONFLICT (user_id, paper_id) DO UPDATE SET status = EXCLUDED.status, updated_at = now()
        """,
        (user_id, paper_id, status),
    )