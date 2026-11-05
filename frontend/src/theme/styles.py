"""Custom CSS and thematic styles for the Ex-Libris frontend.

Provides a Letterboxd-inspired aesthetic adapted for books ('Literary Obsidian').
Features book cover shadows, golden accents, and dark cards.
"""

import streamlit as st

CUSTOM_CSS = """
<style>
/* -------------------------------------------------------------
   EX-LIBRIS : Direction Artistique "Literary Obsidian"
   Inspirée de Letterboxd (fonds sombres, grilles visuelles d'affiches/livres,
   accents or, émeraude et rubis).
-------------------------------------------------------------- */

/* Fond général et typographie de base */
.stApp {
    background-color: #14181c;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* En-tête de section style Letterboxd (tracked uppercase) */
.ex-section-title {
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #8fa0b0;
    border-bottom: 1px solid #232c37;
    padding-bottom: 6px;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.ex-hero-header {
    background: linear-gradient(135deg, #18202a 0%, #101419 100%);
    border: 1px solid #232c37;
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.ex-hero-title {
    font-size: 2.2rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
    margin: 0;
}

.ex-hero-subtitle {
    font-size: 1rem;
    color: #8fa0b0;
    margin-top: 0.5rem;
    line-height: 1.5;
}

/* Carte de livre façon affiche de film / reliure 3D */
.book-poster-container {
    background-color: #1a222c;
    border: 1px solid #26313f;
    border-radius: 8px;
    padding: 10px;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    display: flex;
    flex-direction: column;
    height: 100%;
}

.book-poster-container:hover {
    transform: translateY(-4px);
    border-color: #e5a93c;
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.5);
}

.book-cover-wrapper {
    width: 100%;
    aspect-ratio: 2 / 3;
    position: relative;
    border-radius: 4px;
    overflow: hidden;
    background-color: #10151c;
}

.book-cover-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 4px;
    box-shadow: inset 4px 0 8px rgba(0, 0, 0, 0.6), 0 4px 10px rgba(0, 0, 0, 0.3);
    display: block;
}

.book-cover-placeholder {
    width: 100%;
    height: 100%;
    aspect-ratio: 2 / 3;
    border-radius: 4px;
    background: linear-gradient(145deg, #1f2833 0%, #121820 100%);
    border: 1px solid #2e3a49;
    box-shadow: inset 5px 0 10px rgba(0, 0, 0, 0.7);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 12px 10px;
    text-align: center;
    box-sizing: border-box;
}

.placeholder-icon {
    font-size: 1.4rem;
    opacity: 0.85;
}

.placeholder-title {
    font-size: 0.82rem;
    font-weight: 700;
    color: #e5a93c;
    line-height: 1.3;
    max-height: 4.8em;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
}

.placeholder-author {
    font-size: 0.72rem;
    color: #8fa0b0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.book-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #ffffff;
    margin-top: 8px;
    line-height: 1.25;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.book-author {
    font-size: 0.8rem;
    color: #8fa0b0;
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Badges de statuts de lecture */
.badge-status {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.badge-reading {
    background-color: rgba(0, 199, 118, 0.15);
    color: #00e054;
    border: 1px solid rgba(0, 199, 118, 0.3);
}

.badge-completed {
    background-color: rgba(229, 169, 60, 0.15);
    color: #e5a93c;
    border: 1px solid rgba(229, 169, 60, 0.3);
}

.badge-to-read {
    background-color: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
}

.badge-favorite {
    background-color: rgba(244, 63, 94, 0.15);
    color: #f43f5e;
    border: 1px solid rgba(244, 63, 94, 0.3);
}

.badge-xp {
    background: linear-gradient(135deg, #e5a93c 0%, #d48b19 100%);
    color: #14181c;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    box-shadow: 0 2px 6px rgba(229, 169, 60, 0.3);
}

/* Carte de Quête Gamifiée */
.quest-card {
    background-color: #1a222c;
    border: 1px solid #283341;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: border-color 0.2s ease;
}

.quest-card.completed {
    border-color: #e5a93c;
    background: linear-gradient(135deg, #1c2633 0%, #171f29 100%);
}

.quest-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.quest-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #ffffff;
}

.quest-desc {
    font-size: 0.88rem;
    color: #94a3b8;
    line-height: 1.4;
}

.quest-progress-bg {
    width: 100%;
    height: 8px;
    background-color: #263240;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 6px;
}

.quest-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #e5a93c 0%, #fcd34d 100%);
    border-radius: 999px;
}

/* Étoiles d'évaluation */
.rating-stars {
    color: #e5a93c;
    font-size: 0.9rem;
    letter-spacing: 2px;
}

/* Boutons stylisés */
div.stButton > button:first-child {
    background-color: #e5a93c;
    color: #14181c;
    font-weight: 700;
    border-radius: 6px;
    border: none;
    padding: 0.5rem 1rem;
    transition: all 0.2s ease;
}

div.stButton > button:first-child:hover {
    background-color: #f3b74e;
    color: #000000;
    box-shadow: 0 4px 12px rgba(229, 169, 60, 0.35);
    border: none;
}

/* Inputs Streamlit */
div[data-baseweb="input"] {
    background-color: #1c242e !important;
    border-color: #2b3644 !important;
    border-radius: 6px !important;
}

div[data-baseweb="input"]:focus-within {
    border-color: #e5a93c !important;
}

/* Masquer les bannières par défaut de Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent !important;}
</style>
"""


def apply_custom_css() -> None:
    """Inject custom Letterboxd-like CSS into the current Streamlit page."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_section_title(title: str, subtitle: str = "") -> None:
    """Render a tracked uppercase section divider in Letterboxd style.

    :param title: Main section title
    :param subtitle: Optional counter or right-aligned subtitle
    """
    sub_html = f"<span>{subtitle}</span>" if subtitle else ""
    st.markdown(
        f'<div class="ex-section-title"><span>{title}</span>{sub_html}</div>',
        unsafe_allow_html=True,
    )
