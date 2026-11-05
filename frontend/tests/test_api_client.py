"""Unit tests for the frontend APIClient."""

from unittest.mock import Mock, patch

from utils.api_client import APIClient


def test_api_client_resolve_url():
    """Verify endpoint path resolution with /api prefix."""
    client = APIClient(base_url="http://testserver:8000")

    assert client._resolve_url("/auth/login") == "http://testserver:8000/api/auth/login"
    assert client._resolve_url("auth/login") == "http://testserver:8000/api/auth/login"
    assert client._resolve_url("/api/books") == "http://testserver:8000/api/books"


@patch("requests.Session.request")
def test_api_client_request_success(mock_request):
    """Verify successful request returns parsed data and status code."""
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id_book": 1, "title": "Dune"}]
    mock_request.return_value = mock_resp

    client = APIClient(base_url="http://testserver:8000")
    result = client.get("/books")

    assert result["success"] is True
    assert result["status_code"] == 200
    assert len(result["data"]) == 1
    assert result["data"][0]["title"] == "Dune"
    assert result["error"] is None


@patch("requests.Session.request")
def test_api_client_request_failure(mock_request):
    """Verify HTTP error extracts detail message from payload."""
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"detail": "Incorrect credentials."}
    mock_request.return_value = mock_resp

    client = APIClient(base_url="http://testserver:8000")
    result = client.login("wrong", "pwd")

    assert result["success"] is False
    assert result["status_code"] == 401
    assert result["error"] == "Incorrect credentials."
