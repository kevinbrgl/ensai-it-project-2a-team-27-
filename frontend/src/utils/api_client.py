"""Centralized API client for communicating with the FastAPI backend.

Handles authentication headers, route prefixes, and request error formatting.
"""

import os
from typing import Any

import requests
import streamlit as st


def get_backend_url() -> str:
    """Resolve backend URL, prioritizing 127.0.0.1:8000 over legacy port 5000.

    Replaces 'localhost' with '127.0.0.1' to avoid IPv6 lookup timeouts on Linux.
    :return: Resolved base URL string without trailing slash
    """
    url = os.getenv("BACKEND_URL", "").strip()
    # Default or old template legacy port 5000 -> FastAPI port 8000
    if not url or ":5000" in url:
        return "http://127.0.0.1:8000"
    if "localhost" in url:
        url = url.replace("localhost", "127.0.0.1")
    return url.rstrip("/")


DEFAULT_TIMEOUT = int(os.getenv("BACKEND_TIMEOUT", 15))


class APIClient:
    """Client for making authenticated HTTP requests to the Ex-Libris API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._custom_base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    @property
    def base_url(self) -> str:
        """Return configured base URL or dynamic backend URL."""
        return self._custom_base_url or get_backend_url()

    def is_healthy(self) -> bool:
        """Probe the backend API to check if the server is running.

        :return: True if backend responds within 1.5 seconds, False otherwise
        """
        try:
            resp = self.session.get(f"{self.base_url}/", timeout=1.5)
            return resp.status_code < 500
        except Exception:
            return False

    def _get_headers(self) -> dict[str, str]:
        """Retrieve request headers with Bearer token if user is authenticated."""
        headers = {
            "Accept": "application/json",
        }
        token = st.session_state.get("access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _resolve_url(self, path: str) -> str:
        """Ensure the path has the /api prefix if not already included."""
        clean_path = path.strip()
        if not clean_path.startswith("/"):
            clean_path = f"/{clean_path}"
        if not clean_path.startswith("/api"):
            clean_path = f"/api{clean_path}"
        return f"{self.base_url}{clean_path}"

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute HTTP request and return parsed response dictionary."""
        url = self._resolve_url(path)
        headers = self._get_headers()
        custom_headers = kwargs.pop("headers", {})
        headers.update(custom_headers)

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                timeout=self.timeout,
                **kwargs,
            )

            # Parse JSON body safely
            try:
                payload = response.json()
            except Exception:
                payload = response.text

            is_success = 200 <= response.status_code < 300
            error_message = None
            if not is_success:
                if isinstance(payload, dict):
                    error_message = payload.get("detail", str(payload))
                else:
                    error_message = str(payload)

            return {
                "success": is_success,
                "status_code": response.status_code,
                "data": payload if is_success else None,
                "error": error_message,
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "status_code": 408,
                "data": None,
                "error": (
                    f"Le serveur API ({self.base_url}) n'a pas répondu à temps (Timeout). "
                    "Assurez-vous que le backend FastAPI est bien lancé dans le terminal 1 "
                    "avec la commande : 'uv run src/main.py'."
                ),
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "status_code": 503,
                "data": None,
                "error": (
                    f"Impossible de joindre le serveur API sur {self.base_url}. "
                    "Vérifiez que le backend FastAPI tourne bien dans le terminal 1 "
                    "('uv run src/main.py')."
                ),
            }
        except requests.exceptions.RequestException as exc:
            return {
                "success": False,
                "status_code": 500,
                "data": None,
                "error": f"Erreur réseau: {exc}",
            }

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform a GET request."""
        return self.request("GET", path, params=params)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a POST request."""
        return self.request("POST", path, json=json, data=data)

    def patch(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform a PATCH request."""
        return self.request("PATCH", path, json=json)

    def delete(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform a DELETE request."""
        return self.request("DELETE", path, params=params)

    # -------------------------------------------------------------
    # Méthodes spécifiques de commodité pour Ex-Libris
    # -------------------------------------------------------------

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate with OAuth2 password flow."""
        return self.request(
            "POST",
            "/auth/login",
            data={"username": username, "password": password},
        )

    def register(self, username: str, email: str, password: str) -> dict[str, Any]:
        """Register a new user account."""
        return self.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )

    def get_me(self) -> dict[str, Any]:
        """Retrieve current user profile."""
        return self.get("/users/me")

    def get_quests(self, status_filter: str = "all") -> dict[str, Any]:
        """Retrieve active quests and progress."""
        return self.get("/users/me/quests", params={"status": status_filter})

    def get_catalog(
        self,
        category: str | None = None,
        author: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve catalog books with optional filters."""
        params: dict[str, Any] = {}
        if category:
            params["category"] = category
        if author:
            params["author"] = author
        return self.get("/books", params=params)

    def search_books(self, query: str, limit: int = 20) -> dict[str, Any]:
        """Search books via OpenLibrary integration using query parameter 'q'."""
        return self.get("/books/search", params={"q": query, "limit": limit})

    def get_library(self, status: str | None = None) -> dict[str, Any]:
        """Retrieve current user library books filtered by status."""
        params = {"status": status} if status else None
        return self.get("/library/books", params=params)

    def get_favorites(self) -> dict[str, Any]:
        """Retrieve user's favorite books."""
        return self.get("/library/favorites")

    def add_to_library(self, id_book: int, state: str = "WANT_TO_READ") -> dict[str, Any]:
        """Add a book by internal ID to user library."""
        return self.post(
            "/library/books",
            json={"id_book": id_book, "state": state},
        )

    def update_book_status(self, id_book: int, state: str) -> dict[str, Any]:
        """Update reading status of a book in library."""
        return self.patch(
            f"/library/books/{id_book}/status",
            json={"state": state},
        )

    def toggle_favorite(self, id_book: int) -> dict[str, Any]:
        """Toggle favorite flag on a book in library."""
        return self.post(f"/library/books/{id_book}/favorite")

    def toggle_like(self, id_book: int) -> dict[str, Any]:
        """Toggle like flag on a book in library."""
        return self.post(f"/library/books/{id_book}/like")

    def remove_from_library(self, id_book: int) -> dict[str, Any]:
        """Remove a book from user library."""
        return self.delete(f"/library/books/{id_book}")

    def search_users(self, username: str, limit: int = 10) -> dict[str, Any]:
        """Search other users by username."""
        return self.get("/users/search", params={"username": username, "limit": limit})

    def follow_user(self, user_id: int) -> dict[str, Any]:
        """Follow another user."""
        return self.post(f"/users/{user_id}/follow")

    def unfollow_user(self, user_id: int) -> dict[str, Any]:
        """Unfollow a user."""
        return self.delete(f"/users/{user_id}/follow")

    def get_followers(self, user_id: int) -> dict[str, Any]:
        """List followers of a user."""
        return self.get(f"/users/{user_id}/followers")

    def get_following(self, user_id: int) -> dict[str, Any]:
        """List users followed by a user."""
        return self.get(f"/users/{user_id}/following")


api_client = APIClient()
