"""Book card component for displaying book posters in Letterboxd style.

Provides visual poster rendering, real cover loading, and elegant fallback covers.
"""

import html
from typing import Any

import streamlit as st


def get_cover_url(book: dict[str, Any]) -> str | None:
    """Retrieve book cover URL from book object or Open Library OLID.

    :param book: Dictionary containing book details
    :return: Direct URL to the cover image, or None if unavailable
    """
    # 1. Direct cover_image field stored in DB by books_service
    cover_image = book.get("cover_image") or book.get("cover_url")
    if cover_image and str(cover_image).strip():
        clean_url = str(cover_image).strip()
        if clean_url.startswith("http"):
            return clean_url

    # 2. Derive cover from Open Library identifier (e.g. /works/OL12345W or OL12345M)
    id_api = str(book.get("id_book_api") or "").strip()
    if id_api:
        clean_id = id_api.strip("/").split("/")[-1]
        if clean_id.startswith("OL"):
            return f"https://covers.openlibrary.org/b/olid/{clean_id}-M.jpg"

    return None


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
    raw_title = str(book.get("title") or "Sans titre")
    raw_author = str(book.get("author") or "Auteur inconnu")
    title = html.escape(raw_title)
    author = html.escape(raw_author)
    state = book.get("state")
    category = html.escape(str(book.get("category") or "Littérature"))
    cover_url = get_cover_url(book)

    # Reading state badge
    state_badge_html = ""
    if show_state and state:
        css_class = {
            "READING": "badge-reading",
            "COMPLETED": "badge-completed",
            "WANT_TO_READ": "badge-to-read",
            "TO_READ": "badge-to-read",
            "ABANDONED": "badge-favorite",
        }.get(state, "badge-to-read")

        label = {
            "READING": "En cours 📖",
            "COMPLETED": "Terminé ✅",
            "WANT_TO_READ": "À lire ⏳",
            "TO_READ": "À lire ⏳",
            "ABANDONED": "Abandonné ❌",
        }.get(state, state)

        state_badge_html = f'<span class="badge-status {css_class}">{label}</span>'

    # Cover image or typographic placeholder
    if cover_url:
        cover_html = f"""
        <div class="book-cover-wrapper">
            <img class="book-cover-img" src="{cover_url}" alt="{title}"
                 loading="lazy"
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
            <div class="book-cover-placeholder" style="display: none;">
                <div class="placeholder-icon">📖</div>
                <div class="placeholder-title">{title}</div>
                <div class="placeholder-author">{author}</div>
            </div>
        </div>
        """
    else:
        cover_html = f"""
        <div class="book-cover-wrapper">
            <div class="book-cover-placeholder">
                <div class="placeholder-icon">📖</div>
                <div class="placeholder-title">{title}</div>
                <div class="placeholder-author">{author}</div>
            </div>
        </div>
        """

    card_html = f"""
    <div class="book-poster-container">
        {cover_html}
        <div class="book-title" title="{title}">{title}</div>
        <div class="book-author" title="{author}">{author}</div>
        <div style="margin-top: 6px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.72rem; color: #64748b; text-transform: uppercase;">{category}</span>
            {state_badge_html}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
