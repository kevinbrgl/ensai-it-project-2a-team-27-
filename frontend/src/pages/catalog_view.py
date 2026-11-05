"""Catalog and book discovery view.

Allows searching Open Library, browsing Ex-Libris database, and adding books.
"""

import streamlit as st

from components.book_card import render_book_card
from theme.styles import apply_custom_css, render_section_title
from utils.api_client import api_client
from utils.session import is_authenticated


def render_catalog_page() -> None:
    """Render the book discovery and catalog browser."""
    apply_custom_css()

    st.markdown(
        """
        <div class="ex-hero-header">
            <h1 class="ex-hero-title">EXPLORER LE CATALOGUE</h1>
            <p class="ex-hero-subtitle">
                Recherchez des millions d'ouvrages via Open Library ou parcourez
                notre sélection littéraire pour enrichir vos étagères.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Search Bar
    search_col1, search_col2 = st.columns([4, 1])
    with search_col1:
        query = st.text_input(
            "Recherche de livres",
            placeholder="Titre, auteur, mot-clé...",
            label_visibility="collapsed",
            key="catalog_search_input",
        )
    with search_col2:
        search_btn = st.button("Rechercher 🔍", use_container_width=True)

    # Catégories populaires
    categories = [
        "Toutes les catégories",
        "Science-Fiction",
        "Fantasy",
        "Fiction",
        "Histoire",
        "Philosophie",
        "Romance",
        "Thriller",
    ]
    selected_category = st.selectbox(
        "Filtrer par catégorie",
        options=categories,
        index=0,
        label_visibility="collapsed",
    )

    category_filter = None if selected_category == "Toutes les catégories" else selected_category

    # Fetch books
    books: list[dict] = []
    if (search_btn or query) and query.strip():
        with st.spinner("Recherche en cours..."):
            res = api_client.search_books(query.strip())
            if res["success"]:
                books = res["data"] or []
            else:
                st.error(res["error"] or "Erreur lors de la recherche.")
    else:
        with st.spinner("Chargement des suggestions..."):
            res = api_client.get_catalog(category=category_filter, limit=16)
            if res["success"]:
                books = res["data"] or []

    render_section_title(
        "OUVRAGES DISPONIBLES",
        f"{len(books)} livre{'s' if len(books) > 1 else ''}",
    )

    if not books:
        st.info("Aucun livre trouvé pour ces critères.")
        return

    # Grille de 4 colonnes façon Letterboxd
    cols_count = 4
    for i in range(0, len(books), cols_count):
        row_books = books[i : i + cols_count]
        cols = st.columns(cols_count)
        for col, book in zip(cols, row_books, strict=False):
            with col:
                render_book_card(book, show_state=False)

                if is_authenticated():
                    book_id_api = book.get("id_book_api") or str(book.get("id_book"))
                    with st.popover("➕ Ajouter", use_container_width=True):
                        st.caption(f"Ajouter : {book.get('title')}")
                        state_choice = st.selectbox(
                            "Statut de lecture",
                            options=["TO_READ", "READING", "COMPLETED"],
                            format_func=lambda x: {
                                "TO_READ": "À lire ⏳",
                                "READING": "En cours 📖",
                                "COMPLETED": "Terminé ✅",
                            }.get(x, x),
                            key=f"state_sel_{book_id_api}",
                        )
                        is_fav = st.checkbox("Coup de cœur ❤️", key=f"fav_chk_{book_id_api}")

                        if st.button("Confirmer", key=f"add_btn_{book_id_api}"):
                            add_res = api_client.post(
                                "/library/books",
                                json={
                                    "id_book_api": book.get("id_book_api"),
                                    "state": state_choice,
                                    "is_favorite": is_fav,
                                },
                            )
                            if add_res["success"]:
                                st.toast("Livre ajouté à votre bibliothèque !", icon="📚")
                            else:
                                st.error(add_res["error"] or "Impossible d'ajouter.")


if __name__ == "__main__":
    render_catalog_page()
