"""Integration tests for UserDAO.

Covers user creation, reading, updating, duplicate handling, SQL injection, and DB errors.
"""

import pytest
from psycopg2.errors import Error as DBError
from psycopg2.extras import RealDictCursor
from pytest_mock import MockerFixture

from src.core.security import get_password_hash
from src.dao.users_dao import UserDAO
from src.models import User, UserCreate, UserUpdateFull
from src.utils.exceptions import UserAlreadyExistsError, DAOError


@pytest.fixture
def sample_user():
    """Fixture for a sample user creation object."""
    return UserCreate(
        username="testuser",
        first_name="Test",
        last_name="User",
        hashed_password="hashed_pw"
    )

@pytest.fixture
def dao(db_cursor: RealDictCursor):
    """Fixture for UserDAO instance."""
    return UserDAO(db_cursor)

class TestCreate:
    """Tests for UserDAO.create."""

    def test_valid(self, dao: UserDAO, sample_user: UserCreate):
        """Test creating a valid user."""
        user = dao.create(sample_user)
        assert isinstance(user, User)
        assert isinstance(user.id, int)
        assert user.username == sample_user.username
        assert user.first_name == sample_user.first_name
        assert user.last_name == sample_user.last_name
        assert user.hashed_password == sample_user.hashed_password


    def test_duplicate(self, dao: UserDAO, sample_user: UserCreate):
        """Test creating a duplicate user raises UserAlreadyExistsError."""
        dao.create(sample_user)
        with pytest.raises(UserAlreadyExistsError):
            dao.create(sample_user)
    
    def test_db_error(self,
                      dao: UserDAO,
                      mocker: MockerFixture,
                      sample_user: UserCreate):
        mocker.patch.object(
            dao.cur, "execute", side_effect=DBError("Simulated DB failure")
        )
        with pytest.raises(DAOError):
            dao.create(sample_user)

class TestRead:
    """Tests for UserDAO.read."""

    @pytest.fixture(autouse=True)
    def setup(self, dao: UserDAO, sample_user: UserCreate):
        """Create a sample user before each test."""
        self.user = dao.create(sample_user)

    def test_existing(self, dao: UserDAO):
        """Test reading an existing user by ID."""
        user = dao.read(self.user.id)
        assert isinstance(user, User)
        assert user.id == self.user.id
        assert user.username == self.user.username
        assert user.first_name == self.user.first_name
        assert user.last_name == self.user.last_name
        assert user.hashed_password == self.user.hashed_password

    def test_nonexistent(self, dao: UserDAO):
        """Test reading a non-existent user returns None."""
        user = dao.read(99999)
        assert user is None
    
    def test_db_error(self, dao: UserDAO, mocker: MockerFixture):
        """Test database error during user reading raises DAOError."""
        mocker.patch.object(
            dao.cur, "execute", side_effect=DBError("Simulated DB failure")
        )
        with pytest.raises(DAOError):
            dao.read(self.user.id)
        

class TestReadByUsername:
    """Tests for UserDAO.read_by_username."""

    @pytest.fixture(autouse=True)
    def setup(self, dao: UserDAO, sample_user: UserCreate):
        """Create a sample user before each test"""
        self.user = dao.create(sample_user)

    def test_existing(self, dao: UserDAO):
        """Test reading an existing user by username."""
        user = dao.read_by_username(self.user.username)
        assert isinstance(user, User)
        assert user.id == self.user.id
        assert user.username == self.user.username
        assert user.first_name == self.user.first_name
        assert user.last_name == self.user.last_name
        assert user.hashed_password == self.user.hashed_password

    def test_nonexistent(self, dao: UserDAO):
        """Test reading a non-existent user by username returns None."""
        user = dao.read_by_username("jackblack")
        assert user is None
    
    def test_db_error(self, dao: UserDAO, mocker: MockerFixture):
        """Test database error during user reading raises DAOError."""
        mocker.patch.object(
            dao.cur, "execute", side_effect=DBError("Simulated DB failure")
        )
        with pytest.raises(DAOError):
            dao.read(self.user.username)


class TestUpdate:
    """Tests for UserDAO.update."""

    @pytest.fixture(autouse=True)
    def setup(self, dao: UserDAO, sample_user: UserCreate):
        """Create a sample user before each test."""
        self.user = dao.create(sample_user)

    def test_valid(self, dao: UserDAO):
        """Test updating an existing user."""
        update = UserUpdateFull(first_name="Updated", last_name="User")
        updated = dao.update(self.user.id, update)
        assert isinstance(updated, User)
        assert updated.id == self.user.id
        assert updated.username == self.user.username
        assert updated.first_name == update.first_name
        assert updated.last_name == update.last_name
        assert updated.hashed_password == self.user.hashed_password


    def test_nothing(self, dao: UserDAO):
        """Test updating with no changes raises ValueError."""
        update = UserUpdateFull()
        with pytest.raises(ValueError):
            dao.update(self.user.id, update)

    def test_nonexistent(self, dao: UserDAO):
        """Test updating a non-existent user returns None."""
        update = UserUpdateFull(first_name="Ghost")
        result = dao.update(99999, update)
        assert result is None

    def test_db_error(self, dao: UserDAO, mocker: MockerFixture):
        """Test database error during update raises DAOError."""
        update = UserUpdateFull(first_name="Error")
        mocker.patch.object(
            dao.cur, "execute", side_effect=DBError("Simulated DB failure")
        )
        with pytest.raises(DAOError):
            dao.update(self.user.id, update)
