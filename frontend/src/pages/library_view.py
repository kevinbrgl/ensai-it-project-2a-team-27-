"""User Library view displaying reading shelves in Letterboxd style.

Supports filtering by reading status, marking favorites, and updating progress.
"""

import streamlit as st

from components.book_card import render_book_card
from theme.styles import apply_custom_css, render_section_title
from utils.api_client import api_client
from utils.session import is_authenticated


def render_library_page() -> None:
    """Render the user personal library organized by shelves."""
    apply_custom_css()

    if not is_authenticated():
        st.warning("Veuillez vous connecter pour accéder à votre bibliothèque personnelle.")
        return

    st.markdown(
        """
        <div class="ex-hero-header">
            <h1 class="ex-hero-title">MA BIBLIOTHÈQUE</h1>
            <p class="ex-hero-subtitle">
                Vos étagères personnelles. Suivez l'avancée de vos lectures,
                notez vos coups de cœur et gérez votre liste d'envies.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_all, tab_reading, tab_completed, tab_toread, tab_favs = st.tabs(
        [
            "📚 Tous",
            "📖 En cours",
            "✅ Livres lus",
            "⏳ À lire",
            "❤️ Coups de cœur",
        ],
    )

    def display_shelf(status_filter: str | None = None, is_favorites: bool = False) -> None:
        with st.spinner("Chargement de vos étagères..."):
            if is_favorites:
                res = api_client.get_favorites()
            else:
                res = api_client.get_library(status=status_filter)

            if not res["success"]:
                st.error(res["error"] or "Impossible de charger la bibliothèque.")
                return

            books = res["data"] or []
            render_section_title(f"ÉTAGÈRE ({len(books)} LIVRE{'S' if len(books) > 1 else ''})")

            if not books:
                st.info("Aucun livre dans cette section pour le moment.")
                return

            cols_count = 4
            for i in range(0, len(books), cols_count):
                row_books = books[i : i + cols_count]
                cols = st.columns(cols_count)
                for col, book in zip(cols, row_books, strict=False):
                    with col:
                        render_book_card(book, show_state=True)
                        book_id = book.get("id_book")
                        if book_id is None:
                            continue

                        with st.popover("⚙️ Gérer", use_container_width=True):
                            current_state = book.get("state", "WANT_TO_READ")
                            state_options = ["WANT_TO_READ", "READING", "COMPLETED"]
                            current_index = (
                                state_options.index(current_state)
                                if current_state in state_options
                                else 0
                            )

                            new_state = st.selectbox(
                                "Changer de statut",
                                options=state_options,
                                index=current_index,
                                format_func=lambda s: {
                                    "WANT_TO_READ": "À lire ⏳",
                                    "READING": "En cours 📖",
                                    "COMPLETED": "Terminé ✅",
                                }.get(s, s),
                                key=f"lib_state_{book_id}",
                            )

                            if new_state != current_state:
                                if st.button("Mettre à jour le statut", key=f"upd_st_{book_id}"):
                                    upd_res = api_client.update_book_status(book_id, new_state)
                                    if upd_res["success"]:
                                        st.toast("Statut mis à jour !", icon="✨")
                                        st.rerun()
                                    else:
                                        st.error(upd_res["error"] or "Erreur de mise à jour.")

                            current_fav = bool(book.get("is_favorite", False))
                            fav_label = (
                                "Retirer des favoris 💔" if current_fav else "Ajouter aux favoris ❤️"
                            )
                            if st.button(fav_label, key=f"fav_btn_{book_id}"):
                                fav_res = api_client.toggle_favorite(book_id)
                                if fav_res["success"]:
                                    st.toast("Favoris mis à jour !", icon="❤️")
                                    st.rerun()
                                else:
                                    st.error(fav_res["error"] or "Erreur favoris.")

                            st.divider()
                            if st.button("Retirer de la bibliothèque 🗑️", key=f"del_btn_{book_id}"):
                                del_res = api_client.remove_from_library(book_id)
                                if del_res["success"]:
                                    st.toast("Livre retiré.", icon="🗑️")
                                    st.rerun()
                                else:
                                    st.error(del_res["error"] or "Erreur lors de la suppression.")

    with tab_all:
        display_shelf(None)
    with tab_reading:
        display_shelf("READING")
    with tab_completed:
        display_shelf("COMPLETED")
    with tab_toread:
        display_shelf("WANT_TO_READ")
    with tab_favs:
        display_shelf(is_favorites=True)


if __name__ == "__main__":
    render_library_page()
