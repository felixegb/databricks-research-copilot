import streamlit as st

st.set_page_config(page_title="Research Copilot", page_icon="📚", layout="wide")

st.markdown(
    """
    <style>
        .block-container {padding-top: 2.5rem; padding-bottom: 2rem; max-width: 1100px;}
        .rc-paper-title {font-size: 0.95rem; font-weight: 600; margin-bottom: 0.1rem;}
        .rc-paper-meta {font-size: 0.8rem; color: #868e96;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

from data import (
    get_current_email, get_or_create_user, list_collections, create_collection,
    list_collection_papers, remove_paper_from_collection, search_papers_by_title,
    add_paper_to_collection, list_progress, set_progress,
)
from agent_client import ask_agent

email = get_current_email()
user_id = get_or_create_user(email)

STATUS_LABELS = {"not_started": "Sin empezar", "reading": "Leyendo", "done": "Terminado"}
STATUSES = list(STATUS_LABELS.keys())

with st.sidebar:
    st.markdown("### 📚 Research Copilot")
    st.caption(email)
    st.divider()
    all_collections = list_collections(user_id)
    all_progress = list_progress(user_id)
    done_count = sum(1 for p in all_progress if p["status"] == "done")
    c1, c2 = st.columns(2)
    c1.metric("Colecciones", len(all_collections))
    c2.metric("Leídos", done_count)

st.markdown("## Copiloto de Investigación")
st.caption("Chat, colecciones y seguimiento de lectura sobre tu base de papers")

tab_chat, tab_collections, tab_progress = st.tabs(["💬 Chat", "📁 Colecciones", "📊 Progreso"])

with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])
    prompt = st.chat_input("Pregunta algo sobre papers...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Buscando..."):
                reply = ask_agent(st.session_state.messages)
            st.write(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

with tab_collections:
    with st.expander("➕ Nueva colección"):
        with st.form("nueva_coleccion", clear_on_submit=True):
            name = st.text_input(
                "Nombre", label_visibility="collapsed", placeholder="Nombre de la colección"
            )
            submitted = st.form_submit_button("Crear", use_container_width=True)
            if submitted and name:
                create_collection(user_id, name)
                st.rerun()

    collections = list_collections(user_id)
    if not collections:
        st.info("Todavía no tienes colecciones. Crea una arriba.")

    for c in collections:
        with st.container(border=True):
            st.markdown(
                f"**{c['name']}** &nbsp; "
                f"<span class='rc-paper-meta'>{c['n_papers']} papers</span>",
                unsafe_allow_html=True,
            )
            papers = list_collection_papers(c["collection_id"], user_id)
            for p in papers:
                col1, col2, col3 = st.columns([6, 2, 1])
                with col1:
                    st.markdown(
                        f"<div class='rc-paper-title'>{p['title']}</div>"
                        f"<div class='rc-paper-meta'>{p['publication_year'] or 's/f'} · "
                        f"{p['doi'] or p['oa_url'] or 'sin enlace'}</div>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    new_status = st.selectbox(
                        "Estado", STATUSES, index=STATUSES.index(p["status"]),
                        format_func=lambda s: STATUS_LABELS[s],
                        label_visibility="collapsed",
                        key=f"status-{c['collection_id']}-{p['paper_id']}",
                    )
                    if new_status != p["status"]:
                        set_progress(user_id, p["paper_id"], new_status)
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"rm-{c['collection_id']}-{p['paper_id']}", help="Quitar de la colección"):
                        remove_paper_from_collection(c["collection_id"], p["paper_id"])
                        st.rerun()

            with st.popover("➕ Agregar paper"):
                query = st.text_input("Buscar por título", key=f"search-{c['collection_id']}")
                if query:
                    results = search_papers_by_title(query)
                    if not results:
                        st.caption("Sin resultados")
                    for r in results:
                        col_a, col_b = st.columns([5, 1])
                        col_a.write(r["title"])
                        if col_b.button("+", key=f"add-{c['collection_id']}-{r['paper_id']}"):
                            add_paper_to_collection(c["collection_id"], r["paper_id"])
                            st.rerun()

with tab_progress:
    progress = list_progress(user_id)
    if not progress:
        st.info("Todavía no tienes progreso registrado — agrega papers a una colección primero.")
    else:
        for status_key in STATUSES:
            group = [p for p in progress if p["status"] == status_key]
            if not group:
                continue
            st.markdown(f"#### {STATUS_LABELS[status_key]} ({len(group)})")
            for p in group:
                with st.container(border=True):
                    col1, col2 = st.columns([5, 2])
                    col1.markdown(f"<div class='rc-paper-title'>{p['title']}</div>", unsafe_allow_html=True)
                    new_status = col2.selectbox(
                        "Estado", STATUSES, index=STATUSES.index(p["status"]),
                        format_func=lambda s: STATUS_LABELS[s],
                        label_visibility="collapsed",
                        key=f"progress-{p['paper_id']}",
                    )
                    if new_status != p["status"]:
                        set_progress(user_id, p["paper_id"], new_status)
                        st.rerun()