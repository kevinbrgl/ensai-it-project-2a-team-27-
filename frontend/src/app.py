"""Main entry point for the Ex-Libris Streamlit frontend.

Orchestrates navigation, global layout, theme application, and session tracking.
"""

import streamlit as st

from theme.styles import apply_custom_css
from utils.env_variables import load_environment_variables
from utils.log_init import initialize_logs
from utils.session import clear_session, get_current_user, init_session, is_authenticated

# Configure Streamlit page
st.set_page_config(
    page_title="Ex-Libris — Journal de lecture",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize logs & environment
if "logs_initialized" not in st.session_state:
    initialize_logs("Ex-Libris Frontend")
    load_environment_variables()
    st.session_state.logs_initialized = True

init_session()
apply_custom_css()

# Configure Multi-Page Navigation with st.navigation
pages_dict: dict[str, list[st.Page]] = {}

if is_authenticated():
    user = get_current_user() or {}
    username = user.get("username", "Lecteur")

    with st.sidebar:
        st.markdown(
            f"""
            <div style="background: #1a222c; border: 1px solid #283341; border-radius: 8px; padding: 12px; margin-bottom: 1rem;">
                <div style="font-size: 0.75rem; text-transform: uppercase; color: #8fa0b0; font-weight: 700;">Connecté en tant que</div>
                <div style="font-size: 1.15rem; font-weight: 800; color: #e5a93c; margin-top: 2px;">@{username}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Se déconnecter 🚪", use_container_width=True):
            clear_session()
            st.rerun()

    pages_dict = {
        "Découverte": [
            st.Page("pages/catalog_view.py", title="Explorer le catalogue", icon="🔍"),
        ],
        "Mon Espace": [
            st.Page("pages/library_view.py", title="Ma Bibliothèque", icon="📚"),
            st.Page("pages/quests_view.py", title="Quêtes & Défis", icon="⚔️"),
            st.Page("pages/social_view.py", title="Communauté", icon="👥"),
        ],
    }
else:
    with st.sidebar:
        st.markdown(
            """
            <div style="background: #1a222c; border: 1px solid #283341; border-radius: 8px; padding: 12px; margin-bottom: 1rem;">
                <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff;">Bienvenue sur Ex-Libris</div>
                <div style="font-size: 0.85rem; color: #8fa0b0; margin-top: 4px;">Connectez-vous pour gérer votre bibliothèque et accomplir des quêtes.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    pages_dict = {
        "Accès": [
            st.Page("pages/auth_view.py", title="Connexion / Inscription", icon="🔑"),
            st.Page("pages/catalog_view.py", title="Explorer le catalogue", icon="🔍"),
        ],
    }

pg = st.navigation(pages_dict)
pg.run()
