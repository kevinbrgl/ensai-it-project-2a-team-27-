"""Shared mocks for the tests."""

from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.users_dao import UserDAO


@pytest.fixture
def mock_user_dao(mocker: MockerFixture) -> Mock:
    """Return a generic mock DAO that can be customized per test."""
    return mocker.Mock(spec=UserDAO)
