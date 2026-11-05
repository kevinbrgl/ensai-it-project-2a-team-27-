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

    if not is_authenticated():
        st.info(
            "💡 Connectez-vous via l'onglet **Connexion** pour rechercher et ajouter des livres."
        )
        return

    # Search Bar
    search_col1, search_col2 = st.columns([4, 1])
    with search_col1:
        query = st.text_input(
            "Recherche de livres",
            placeholder="Titre (ex: Dune, Le Petit Prince...), auteur...",
            label_visibility="collapsed",
            key="catalog_search_input",
        )
    with search_col2:
        search_btn = st.button("Rechercher 🔍", use_container_width=True)

    # Catégories populaires pour filtrer le catalogue existant
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
        with st.spinner("Recherche sur Open Library et synchronisation..."):
            res = api_client.search_books(query=query.strip(), limit=20)
            if res["success"]:
                books = res["data"] or []
            else:
                st.error(res["error"] or "Erreur lors de la recherche.")
    else:
        with st.spinner("Chargement des suggestions du catalogue..."):
            res = api_client.get_catalog(category=category_filter)
            if res["success"]:
                books = res["data"] or []
            else:
                st.error(res["error"] or "Erreur lors du chargement.")

    render_section_title(
        "OUVRAGES DISPONIBLES",
        f"{len(books)} livre{'s' if len(books) > 1 else ''}",
    )

    if not books:
        st.info("Aucun livre trouvé. Essayez une recherche par titre ou auteur.")
        return

    # Grille de 4 colonnes façon Letterboxd
    cols_count = 4
    for i in range(0, len(books), cols_count):
        row_books = books[i : i + cols_count]
        cols = st.columns(cols_count)
        for col, book in zip(cols, row_books, strict=False):
            with col:
                render_book_card(book, show_state=False)

                book_id = book.get("id_book")
                if book_id is not None:
                    with st.popover("➕ Ajouter", use_container_width=True):
                        st.caption(f"Ajouter : {book.get('title')}")
                        state_choice = st.selectbox(
                            "Statut de lecture",
                            options=["WANT_TO_READ", "READING", "COMPLETED"],
                            format_func=lambda x: {
                                "WANT_TO_READ": "À lire ⏳",
                                "READING": "En cours 📖",
                                "COMPLETED": "Terminé ✅",
                            }.get(x, x),
                            key=f"state_sel_{book_id}",
                        )
                        is_fav = st.checkbox("Coup de cœur ❤️", key=f"fav_chk_{book_id}")

                        if st.button("Confirmer", key=f"add_btn_{book_id}"):
                            add_res = api_client.add_to_library(
                                id_book=int(book_id),
                                state=state_choice,
                            )
                            if add_res["success"]:
                                if is_fav:
                                    api_client.toggle_favorite(int(book_id))
                                st.toast("Livre ajouté à votre bibliothèque !", icon="📚")
                            else:
                                st.error(add_res["error"] or "Impossible d'ajouter.")


if __name__ == "__main__":
    render_catalog_page()
