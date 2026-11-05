"""Authentication view providing Login and Registration forms.

Implements Letterboxd-inspired minimalist card style.
"""

import streamlit as st

from theme.styles import apply_custom_css
from utils.api_client import api_client
from utils.session import is_authenticated, set_user_session


def render_auth_page() -> None:
    """Render Login and Registration tabs for unauthenticated users."""
    apply_custom_css()

    st.markdown(
        """
        <div class="ex-hero-header" style="text-align: center; max-width: 650px; margin: 2rem auto;">
            <div style="font-size: 2.8rem; margin-bottom: 0.5rem;">📖</div>
            <h1 class="ex-hero-title">EX-LIBRIS</h1>
            <p class="ex-hero-subtitle">
                Votre carnet de bord littéraire. Suivez vos lectures,
                découvrez de nouveaux genres et accomplissez vos quêtes.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["🔑 Se connecter", "✨ Créer un compte"])

        with tab_login:
            st.markdown("### Connexion")
            login_user = st.text_input("Nom d'utilisateur", key="login_username")
            login_pwd = st.text_input("Mot de passe", type="password", key="login_password")

            if st.button("Connexion", use_container_width=True, key="btn_login"):
                if not login_user or not login_pwd:
                    st.error("Veuillez renseigner tous les champs.")
                else:
                    with st.spinner("Connexion en cours..."):
                        res = api_client.login(login_user.strip(), login_pwd)
                        if res["success"]:
                            token = res["data"]["access_token"]
                            # Fetch user profile with the new token
                            st.session_state.access_token = token
                            user_res = api_client.get_me()
                            if user_res["success"]:
                                set_user_session(token, user_res["data"])
                                st.success("Connexion réussie !")
                                st.rerun()
                            else:
                                st.error("Impossible de charger le profil.")
                        else:
                            st.error(res["error"] or "Identifiants incorrects.")

        with tab_register:
            st.markdown("### Rejoindre Ex-Libris")
            reg_user = st.text_input("Nom d'utilisateur", key="reg_username")
            reg_email = st.text_input("Adresse e-mail", key="reg_email")
            reg_pwd = st.text_input("Mot de passe", type="password", key="reg_password")

            if st.button("S'inscrire", use_container_width=True, key="btn_register"):
                if not reg_user or not reg_email or not reg_pwd:
                    st.error("Veuillez renseigner tous les champs.")
                elif len(reg_pwd) < 8:
                    st.error("Le mot de passe doit contenir au moins 8 caractères.")
                else:
                    with st.spinner("Création de votre compte..."):
                        res = api_client.register(
                            reg_user.strip(),
                            reg_email.strip(),
                            reg_pwd,
                        )
                        if res["success"]:
                            st.success("Compte créé avec succès ! Connectez-vous dès maintenant.")
                        else:
                            st.error(res["error"] or "Erreur lors de l'inscription.")


if __name__ == "__main__" or is_authenticated():
    render_auth_page()
