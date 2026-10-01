"""Service layer for user operations.

This module provides business logic for user-related operations.
Exceptions are raised for not found, authentication, or password errors.
"""
from src.core.security import get_password_hash, verify_password
from src.dao.users import UserDAO
from src.models import (
    User,
    UserCreate,
    UserRegister,
    UserUpdate,
    UserUpdateFull,
    UserUpdatePassword,
)
from src.utils.exceptions import (
    AuthError,
    IncorrectPasswordError,
    SamePasswordError,
    UserNotFoundError,
)


class UserService:
    """Service class for user business logic.

    :attr dao: Associated UserDAO object
    """

    def __init__(self, user_dao: UserDAO) -> None:
        """Initialize UserService with a database cursor.

        :param cursor: Database cursor
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
        if not verify_password(password, db_user.hashed_password):
            raise AuthError
        return db_user

    def register(self, user_in: UserRegister) -> User:
        """Register a new user.

        :param user_in: User registration data
        :return: The created User object
        """
        user_create = UserCreate.model_validate(
            {
                **user_in.model_dump(),
                "hashed_password": get_password_hash(user_in.password),
            },
            from_attributes=True,
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

        :param user: The user object
        :param body: Password update data
        :raises IncorrectPasswordError: Raised if current password is incorrect
        :raises SamePasswordError: Raised if new password is the same as old
        :raises UserNotFoundError: Raised if user is not found after update
        :return: The updated User object
        """
        if not verify_password(body.current_password,
                               current_user.hashed_password):
            raise IncorrectPasswordError
        if body.current_password == body.new_password:
            raise SamePasswordError

        user = self.dao.update(
            current_user.id,
            UserUpdateFull(
                hashed_password=get_password_hash(body.new_password),
            ),
        )

        if user is None:
            raise UserNotFoundError(user_id=current_user.id)
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
