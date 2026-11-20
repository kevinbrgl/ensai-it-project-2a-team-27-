"""HTTP client for Open Library searches and edition lookups."""

import logging
from typing import Any

import httpx2

from src.utils.exceptions import ExternalServiceError, InvalidSearchQueryError

logger = logging.getLogger(__name__)

OPEN_LIBRARY_URL = "https://openlibrary.org"
OPEN_LIBRARY_SEARCH_URL = f"{OPEN_LIBRARY_URL}/search.json"
OPEN_LIBRARY_FIELDS = (
    "key,title,author_name,subject,first_publish_year,cover_i,"
    "ratings_average,number_of_pages_median"
)
EDITIONS_LIMIT = 20
HTTP_ERROR_STATUS = 400
HTTP_UNPROCESSABLE_STATUS = 422


class OpenLibraryClient:
    """Read search and edition payloads from Open Library."""

    def __init__(self, timeout: float = 5.0) -> None:
        """Set the timeout in seconds for each HTTP request."""
        self.timeout = timeout

    def _get_json(
        self,
        url: str,
        params: dict[str, str | int],
    ) -> dict[str, Any]:
        """Send a GET request to Open Library and return its JSON payload.

        Parameters
        ----------
        url : str
            Open Library URL to call.
        params : dict[str, str | int]
            Query string parameters.

        Returns
        -------
        dict[str, Any]
            JSON payload returned by Open Library.

        Raises
        ------
        InvalidSearchQueryError
            If Open Library rejects the query (HTTP 422), e.g. "the".
        ExternalServiceError
            If the request fails or the response is invalid.

        """
        headers = {"User-Agent": "Ex-Libris/1.0 (contact@ex-libris.fr)"}

        try:
            with httpx2.Client(timeout=self.timeout) as client:
                response = client.get(
                    url,
                    params=params,
                    headers=headers,
                )
        except httpx2.HTTPError as exc:
            logger.warning("Open Library HTTP error: %s", exc)
            raise ExternalServiceError from exc
        except Exception as exc:
            logger.exception("Unexpected error querying Open Library")
            raise ExternalServiceError from exc

        if response.status_code == HTTP_UNPROCESSABLE_STATUS:
            logger.info("Open Library rejected the query: %s", params)
            raise InvalidSearchQueryError

        if response.status_code >= HTTP_ERROR_STATUS:
            logger.error(
                "Open Library returned HTTP error %d",
                response.status_code,
            )
            raise ExternalServiceError

        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning("Open Library returned invalid JSON: %s", exc)
            raise ExternalServiceError from exc

        if not isinstance(payload, dict):
            logger.warning("Open Library returned an unexpected payload")
            raise ExternalServiceError
        return payload

    def search(
        self,
        query: str | None = None,
        limit: int = 10,
        *,
        subject: str | None = None,
        sort: str | None = None,
    ) -> dict[str, Any]:
        """Fetch search results from Open Library.

        Parameters
        ----------
        query : str | None, optional
            Free-text search query (title or author).
        limit : int, optional
            Maximum number of results to fetch.
        subject : str | None, optional
            Subject (genre) filter.
        sort : str | None, optional
            Open Library sort order (e.g. "rating").

        Returns
        -------
        dict[str, Any]
            JSON payload returned by Open Library.

        Notes
        -----
        A failed request or invalid response raises ``ExternalServiceError``.

        """
        params: dict[str, str | int] = {
            "limit": limit,
            "fields": OPEN_LIBRARY_FIELDS,
        }
        if query:
            params["q"] = query
        if subject:
            params["subject"] = subject
        if sort:
            params["sort"] = sort

        return self._get_json(OPEN_LIBRARY_SEARCH_URL, params)

    def fetch_editions(
        self,
        work_key: str,
        limit: int = EDITIONS_LIMIT,
    ) -> dict[str, Any]:
        """Fetch the editions of a work from Open Library.

        Parameters
        ----------
        work_key : str
            Open Library work key (e.g. "/works/OL123W").
        limit : int, optional
            Maximum number of editions to fetch.

        Returns
        -------
        dict[str, Any]
            JSON payload returned by Open Library.

        Notes
        -----
        A failed request or invalid response raises ``ExternalServiceError``.

        """
        return self._get_json(
            f"{OPEN_LIBRARY_URL}{work_key}/editions.json",
            {"limit": limit},
        )
