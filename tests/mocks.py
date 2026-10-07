from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from src.dao.users_dao import UserDAO


@pytest.fixture
def mock_user_dao(mocker: MockerFixture) -> Mock:
    """Return a generic mock DAO that can be customized per test."""
    dao_mock = mocker.Mock(spec=UserDAO)
    return dao_mock
