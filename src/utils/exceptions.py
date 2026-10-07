"""Custom exception classes for application errors.

Defines exceptions for user, item, authentication, and DAO errors.
"""


class UserNotFoundError(Exception):
    """Raised when a user is not found.

    :param user_id: ID of the user (optional)
    :param username: Username of the user (optional)
    """

    def __init__(self,
                 user_id: int | None = None,
                 username: str | None = None) -> None:
        """Initialize UserNotFoundError.

        :param user_id: ID of the user (optional)
        :param username: Username of the user (optional)
        :return: None
        """
        if user_id:
            msg = f"No user found for id={user_id}"
        elif username:
            msg = f"No user found for username='{username}'"
        else:
            msg = "No user found"
        super().__init__(msg)


class DAOError(Exception):
    """Raised for errors in the Data Access Object (DAO) layer.

    :param message: Error message (optional)
    """

    def __init__(self, message: str | None = None) -> None:
        """Initialize DAOError.

        :param message: Error message (optional)
        :return: None
        """
        if message is None:
            message = "Something went wrong in the DAO."
        super().__init__(message)


class AuthError(Exception):
    """Raised for authentication errors."""

    def __init__(self) -> None:
        """Initialize AuthError.

        :return: None
        """
        super().__init__("Could not validate credentials")


class IncorrectPasswordError(Exception):
    """Raised when an incorrect password is provided."""

    def __init__(self) -> None:
        """Initialize IncorrectPasswordError.

        :return: None
        """
        super().__init__("Incorrect password provided")


class SamePasswordError(Exception):
    """Raised when the new password is the same as the old password."""

    def __init__(self) -> None:
        """Initialize SamePasswordError.

        :return: None
        """
        super().__init__("New password must be different from the old one.")


class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an existing username.

    :param username: Username that already exists
    """

    def __init__(self, username: str) -> None:
        """Initialize UserAlreadyExistsError.

        :param username: Username that already exists
        :return: None
        """
        super().__init__(f"Username {username} already exists")


class EmailAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an existing email.

    :param email: Email that already exists
    """

    def __init__(self, email: str) -> None:
        """Initialize EmailAlreadyExistsError.

        :param email: Email that already exists
        :return: None
        """
        super().__init__(f"Email {email} already exists")
