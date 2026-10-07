"""Service layer for user operations.

This module provides business logic for user-related operations.
Exceptions are raised for not found, duplicates, authentication
or password errors.
"""

from src.core.security import get_password_hash, verify_password
from src.dao.users_dao import UserDAO
from src.models.users import (
    User,
    UserCreate,
    UserRegister,
    UserUpdate,
    UserUpdateFull,
    UserUpdatePassword,
)
from src.utils.exceptions import (
    AuthError,
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    SamePasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


class UserService:
    """Service class for user business logic.

    :attr dao: Associated UserDAO object
    """

    def __init__(self, user_dao: UserDAO) -> None:
        """Initialize UserService with a UserDAO.

        :param user_dao: DAO used to access users
        """
        self.dao = user_dao

    def authenticate(self, username: str, password: str) -> User:
        """Authenticate a user by username and password.

        :param username: Username of the user
        :param password: Password of the user
        :raises UserNotFoundError: Raised if user is not found
        :raises AuthError: Raised if password is incorrect
        :return: The authenticated User object
        """
        db_user = self.dao.read_by_username(username)
        if db_user is None:
            raise UserNotFoundError(username=username)
        if not verify_password(password, db_user.password_hash):
            raise AuthError
        return db_user

    def register(self, user_in: UserRegister) -> User:
        """Register a new user.

        :param user_in: User registration data
        :raises UserAlreadyExistsError: Raised if the username is taken
        :raises EmailAlreadyExistsError: Raised if the email is taken
        :return: The created User object
        """
        if self.dao.read_by_username(user_in.username) is not None:
            raise UserAlreadyExistsError(user_in.username)
        if self.dao.read_by_email(user_in.email) is not None:
            raise EmailAlreadyExistsError(user_in.email)

        user_create = UserCreate(
            username=user_in.username,
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
        )
        return self.dao.create(user_create)

    def read(self, user_id: int) -> User:
        """Read a user by their ID.

        :param user_id: ID of the user to read
        :raises UserNotFoundError: Raised if user is not found
        :return: The User object
        """
        user = self.dao.read(user_id)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return user

    def read_by_username(self, username: str) -> User:
        """Read a user by their username.

        :param username: Username of the user to read
        :raises UserNotFoundError: Raised if user is not found
        :return: The User object
        """
        user = self.dao.read_by_username(username)
        if user is None:
            raise UserNotFoundError(username=username)
        return user

    def update_password(self,
                        current_user: User,
                        body: UserUpdatePassword) -> User:
        """Update a user's password.

        :param current_user: The logged-in user
        :param body: Password update data
        :raises IncorrectPasswordError: If current password is incorrect
        :raises SamePasswordError: If new password is the same as old
        :raises UserNotFoundError: If user is not found after update
        :return: The updated User object
        """
        if not verify_password(body.current_password,
                               current_user.password_hash):
            raise IncorrectPasswordError
        if body.current_password == body.new_password:
            raise SamePasswordError

        user = self.dao.update(
            current_user.id_user,
            UserUpdateFull(
                password_hash=get_password_hash(body.new_password),
            ),
        )
        if user is None:
            raise UserNotFoundError(user_id=current_user.id_user)
        return user

    def update(self, user_id: int, user_in: UserUpdate) -> User:
        """Update a user's information.

        :param user_id: ID of the user to update
        :param user_in: User update data
        :raises UserNotFoundError: Raised if user is not found after update
        :return: The updated User object
        """
        user = self.dao.update(
            user_id,
            UserUpdateFull(**user_in.model_dump(exclude_unset=True)),
        )
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return user
