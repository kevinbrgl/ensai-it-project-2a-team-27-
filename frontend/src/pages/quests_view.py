"""Quests and gamification view for the Ex-Libris frontend.

Consumes the GET /api/users/me/quests endpoint to display user missions and XP.
"""

import streamlit as st

from components.quest_card import render_quest_card
from theme.styles import apply_custom_css, render_section_title
from utils.api_client import api_client
from utils.session import is_authenticated


def render_quests_page() -> None:
    """Render active and completed quests with dynamic XP overview."""
    apply_custom_css()

    if not is_authenticated():
        st.warning("Connectez-vous pour suivre vos quêtes et votre progression XP.")
        return

    st.markdown(
        """
        <div class="ex-hero-header">
            <h1 class="ex-hero-title">⚔️ QUÊTES & EXPÉRIENCE</h1>
            <p class="ex-hero-subtitle">
                Relevez des défis de lecture, explorez de nouveaux horizons littéraires
                et accumulez de l'expérience pour faire rayonner votre profil de lecteur.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filter_choice = st.radio(
        "Filtre de statut",
        options=["Toutes", "En cours", "Accomplies"],
        horizontal=True,
        label_visibility="collapsed",
    )
    status_map = {
        "Toutes": "all",
        "En cours": "active",
        "Accomplies": "completed",
    }
    status_filter = status_map.get(filter_choice, "all")

    with st.spinner("Calcul de votre progression littéraire..."):
        res = api_client.get_quests(status_filter=status_filter)
        if not res["success"]:
            st.error(res["error"] or "Impossible de récupérer vos quêtes.")
            return

        quests = res["data"] or []

        # Calculer le récapitulatif XP
        total_xp_unlocked = sum(q.get("reward_xp", 0) for q in quests if q.get("is_completed"))
        total_xp_available = sum(q.get("reward_xp", 0) for q in quests)

        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="✨ XP Débloqués",
                value=f"{total_xp_unlocked} / {total_xp_available} XP",
            )
        with col2:
            completed_count = sum(1 for q in quests if q.get("is_completed"))
            st.metric(
                label="🏆 Quêtes terminées",
                value=f"{completed_count} / {len(quests)}",
            )

        render_section_title(
            f"VOS DÉFIS ({len(quests)})",
            "Missions dynamiques",
        )

        if not quests:
            st.info("Aucune quête ne correspond à ce filtre.")
            return

        for quest in quests:
            render_quest_card(quest)


if __name__ == "__main__":
    render_quests_page()
