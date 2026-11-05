"""Social and community view for discovering readers and following friends."""

import streamlit as st

from theme.styles import apply_custom_css, render_section_title
from utils.api_client import api_client
from utils.session import get_current_user, is_authenticated


def render_social_page() -> None:
    """Render community discovery and reader follow interface."""
    apply_custom_css()

    if not is_authenticated():
        st.warning("Connectez-vous pour accéder au réseau de lecteurs.")
        return

    st.markdown(
        """
        <div class="ex-hero-header">
            <h1 class="ex-hero-title">COMMUNAUTÉ LITTÉRAIRE</h1>
            <p class="ex-hero-subtitle">
                Échangez, découvrez d'autres passionnés et suivez les lectures
                de vos amis pour nourrir vos prochaines envies de livres.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_search, tab_network = st.tabs(["🔍 Rechercher des lecteurs", "👥 Mes relations"])

    with tab_search:
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input(
                "Pseudo du lecteur",
                placeholder="Entrez un nom d'utilisateur...",
                key="social_search_query",
            )
        with col2:
            search_btn = st.button("Rechercher 🔎", use_container_width=True)

        if (search_btn or query) and query.strip():
            with st.spinner("Recherche de lecteurs..."):
                res = api_client.search_users(query.strip())
                if res["success"]:
                    users = res["data"] or []
                    render_section_title(f"RÉSULTATS ({len(users)})")

                    my_user = get_current_user() or {}
                    my_id = my_user.get("id_user")

                    if not users:
                        st.info("Aucun lecteur trouvé avec ce nom.")
                    for u in users:
                        u_id = u.get("id_user")
                        u_name = u.get("username")
                        u_bio = u.get("bio") or "Aucune biographie."

                        card_col1, card_col2 = st.columns([4, 1])
                        with card_col1:
                            st.markdown(
                                f"""
                                <div style="background: #1a222c; border: 1px solid #283341; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                                    <div style="font-weight: 700; color: #ffffff; font-size: 1.05rem;">@{u_name}</div>
                                    <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">{u_bio}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        with card_col2:
                            if u_id != my_id:
                                if st.button(
                                    "Suivre ➕", key=f"follow_{u_id}", use_container_width=True
                                ):
                                    f_res = api_client.follow_user(u_id)
                                    if f_res["success"]:
                                        st.toast(f"Vous suivez maintenant @{u_name} !", icon="🤝")
                                    else:
                                        st.error(
                                            f_res["error"]
                                            or "Impossible de suivre cet utilisateur."
                                        )
                else:
                    st.error(res["error"] or "Erreur lors de la recherche.")

    with tab_network:
        my_user = get_current_user() or {}
        my_id = my_user.get("id_user")
        if not my_id:
            st.info("Profil non disponible.")
            return

        with st.spinner("Chargement de vos relations..."):
            f_res = api_client.get(f"/users/{my_id}/following")
            followers_res = api_client.get(f"/users/{my_id}/followers")

            following_list = f_res.get("data") or [] if f_res["success"] else []
            followers_list = followers_res.get("data") or [] if followers_res["success"] else []

            col_sub1, col_sub2 = st.columns(2)
            with col_sub1:
                render_section_title(f"ABONNEMENTS ({len(following_list)})")
                if not following_list:
                    st.caption("Vous ne suivez aucun lecteur pour l'instant.")
                for f in following_list:
                    f_id = f.get("id_user")
                    f_name = f.get("username")
                    r_col1, r_col2 = st.columns([3, 1])
                    with r_col1:
                        st.markdown(f"**@{f_name}**")
                    with r_col2:
                        if st.button("Ne plus suivre", key=f"unf_{f_id}"):
                            u_res = api_client.unfollow_user(f_id)
                            if u_res["success"]:
                                st.toast(f"Désabonné de @{f_name}")
                                st.rerun()
                            else:
                                st.error(u_res["error"] or "Erreur")

            with col_sub2:
                render_section_title(f"ABONNÉS ({len(followers_list)})")
                if not followers_list:
                    st.caption("Aucun abonné pour le moment.")
                for f in followers_list:
                    st.markdown(f"**@{f.get('username')}**")


if __name__ == "__main__":
    render_social_page()
