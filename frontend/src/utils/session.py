"""Session management module for the Ex-Libris frontend.

Centralizes token storage, user state, and login/logout lifecycles.
"""

from typing import Any

import streamlit as st


def init_session() -> None:
    """Initialize essential keys in Streamlit session_state if absent."""
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "current_user" not in st.session_state:
        st.session_state.current_user = None


def is_authenticated() -> bool:
    """Check if an active authenticated user session exists.

    :return: True if access token is present, False otherwise
    """
    init_session()
    return bool(st.session_state.access_token)


def get_token() -> str | None:
    """Return the current access token.

    :return: Bearer token string or None
    """
    init_session()
    return st.session_state.access_token


def get_current_user() -> dict[str, Any] | None:
    """Return the current authenticated user profile dictionary.

    :return: User dict or None
    """
    init_session()
    return st.session_state.current_user


def set_user_session(token: str, user_data: dict[str, Any]) -> None:
    """Save authentication token and user data into session_state.

    :param token: JWT access token
    :param user_data: User dictionary from /api/users/me
    """
    st.session_state.access_token = token
    st.session_state.current_user = user_data


def clear_session() -> None:
    """Reset session state to log out the user."""
    st.session_state.access_token = None
    st.session_state.current_user = None
