"""Authentication guard utilities for page access control."""

import logging

import streamlit as st

from utils.session import is_authenticated


def check_authentification() -> bool:
    """Check if the user is authenticated.

    :return: True if authenticated, False otherwise
    """
    if not is_authenticated():
        logging.info("User is not authenticated.")
        st.warning("Vous devez être connecté pour accéder à cette page.")
        return False
    return True
