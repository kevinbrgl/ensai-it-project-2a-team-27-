"""Unit tests for frontend session management."""

import streamlit as st

from utils.session import (
    clear_session,
    get_current_user,
    get_token,
    init_session,
    is_authenticated,
    set_user_session,
)


def test_session_lifecycle():
    """Verify session initialization, authentication state, and clearing."""
    st.session_state.clear()
    init_session()

    assert is_authenticated() is False
    assert get_token() is None
    assert get_current_user() is None

    set_user_session(
        token="jwt_fake_token",
        user_data={"id_user": 42, "username": "clara"},
    )

    assert is_authenticated() is True
    assert get_token() == "jwt_fake_token"
    assert get_current_user() == {"id_user": 42, "username": "clara"}

    clear_session()
    assert is_authenticated() is False
    assert get_token() is None
    assert get_current_user() is None
