import streamlit as st

st.set_page_config(page_title="Research Copilot", page_icon="📚", layout="wide")

from data import (
    get_current_email, get_or_create_user, list_collections, create_collection,
    list_collection_papers, remove_paper_from_collection, search_papers_by_title,
    add_paper_to_collection, list_progress, set_progress,
)
from agent_client import ask_agent

email = get_current_email()
user_id = get_or_create_user(email)

st.sidebar.write(f"Usuario: {email}")
page = st.sidebar.radio("Navegacion", ["Chat", "Colecciones", "Progreso"])

STATUSES = ["not_started", "reading", "done"]

if page == "Chat":
    st.title("Chat con el copiloto de investigacion")
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
            with st.spinner("Pensando..."):
                reply = ask_agent(st.session_state.messages)
            st.write(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

elif page == "Colecciones":
    st.title("Mis colecciones")
    with st.form("nueva_coleccion"):
        name = st.text_input("Nombre de la nueva coleccion")
        submitted = st.form_submit_button("Crear")
        if submitted and name:
            create_collection(user_id, name)
            st.success(f"Coleccion '{name}' creada")
            st.rerun()

    collections = list_collections(user_id)
    if not collections:
        st.info("Todavia no tienes colecciones.")
    for c in collections:
        with st.expander(f"{c['name']} ({c['n_papers']} papers)"):
            papers = list_collection_papers(c["collection_id"], user_id)
            for p in papers:
                col1, col2, col3 = st.columns([5, 2, 1])
                col1.write(f"**{p['title']}** ({p['publication_year']}) — {p['doi'] or p['oa_url'] or 'sin enlace'}")
                new_status = col2.selectbox(
                    "Estado", STATUSES, index=STATUSES.index(p["status"]),
                    key=f"status-{c['collection_id']}-{p['paper_id']}",
                )
                if new_status != p["status"]:
                    set_progress(user_id, p["paper_id"], new_status)
                    st.rerun()
                if col3.button("Quitar", key=f"rm-{c['collection_id']}-{p['paper_id']}"):
                    remove_paper_from_collection(c["collection_id"], p["paper_id"])
                    st.rerun()

            st.markdown("**Agregar paper por titulo**")
            query = st.text_input("Buscar", key=f"search-{c['collection_id']}")
            if query:
                results = search_papers_by_title(query)
                for r in results:
                    if st.button(f"+ {r['title']}", key=f"add-{c['collection_id']}-{r['paper_id']}"):
                        add_paper_to_collection(c["collection_id"], r["paper_id"])
                        st.rerun()

elif page == "Progreso":
    st.title("Mi progreso de lectura")
    progress = list_progress(user_id)
    if not progress:
        st.info("Todavia no tienes progreso registrado -- agrega papers a una coleccion primero.")
    for p in progress:
        col1, col2 = st.columns([4, 2])
        col1.write(f"**{p['title']}**")
        new_status = col2.selectbox(
            "Estado", STATUSES, index=STATUSES.index(p["status"]),
            key=f"progress-{p['paper_id']}",
        )
        if new_status != p["status"]:
            set_progress(user_id, p["paper_id"], new_status)
            st.rerun()