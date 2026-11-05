"""Book card component for displaying book posters in Letterboxd style.

Provides visual poster rendering, fallback covers, and action buttons.
"""

from typing import Any

import streamlit as st

DEFAULT_COVER = (
    "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&q=80&w=400"
)


def get_cover_url(book: dict[str, Any]) -> str:
    """Retrieve book cover URL from book object or fallback."""
    url = book.get("cover_url") or book.get("thumbnail_url")
    if not url or not str(url).strip():
        # Fallback to Open Library covers if id_book_api starts with OL
        id_api = str(book.get("id_book_api", ""))
        if "OL" in id_api and id_api.endswith("M"):
            return f"https://covers.openlibrary.org/b/id/{id_api}-M.jpg"
        return DEFAULT_COVER
    return str(url)


def render_book_card(
    book: dict[str, Any],
    show_state: bool = True,
    key_prefix: str = "book",
) -> None:
    """Render a single book poster in a Letterboxd-style container.

    :param book: Book dictionary from API
    :param show_state: Whether to render the reading state badge
    :param key_prefix: Prefix for button widget keys
    """
    title = book.get("title", "Sans titre")
    author = book.get("author", "Auteur inconnu")
    state = book.get("state")
    category = book.get("category") or "Général"
    cover = get_cover_url(book)

    state_badge_html = ""
    if show_state and state:
        css_class = {
            "READING": "badge-reading",
            "COMPLETED": "badge-completed",
            "TO_READ": "badge-to-read",
            "ABANDONED": "badge-favorite",
        }.get(state, "badge-to-read")

        label = {
            "READING": "En cours",
            "COMPLETED": "Terminé",
            "TO_READ": "À lire",
            "ABANDONED": "Abandonné",
        }.get(state, state)

        state_badge_html = f'<span class="badge-status {css_class}">{label}</span>'

    card_html = f"""
    <div class="book-poster-container">
        <img class="book-cover-img" src="{cover}" alt="{title}" onerror="this.src='{DEFAULT_COVER}'" />
        <div class="book-title" title="{title}">{title}</div>
        <div class="book-author" title="{author}">{author}</div>
        <div style="margin-top: 6px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.72rem; color: #64748b; text-transform: uppercase;">{category}</span>
            {state_badge_html}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
