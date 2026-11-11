"""Custom exception classes for application errors.

Defines exceptions for user, item, authentication, and DAO errors.
"""

from datetime import UTC, datetime


class UserNotFoundError(Exception):
    """Raised when a user is not found.

    :param user_id: ID of the user (optional)
    :param username: Username of the user (optional)
    """

    def __init__(
        self,
        user_id: int | None = None,
        username: str | None = None,
    ) -> None:
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


class ExternalServiceError(Exception):
    """Raised when an external service is unavailable.

    :param message: Error message (optional)
    """

    def __init__(self, message: str | None = None) -> None:
        """Initialize ExternalServiceError.

        :param message: Error message (optional)
        :return: None
        """
        if message is None:
            message = "External service is currently unavailable."
        super().__init__(message)


ExternalServiceException = ExternalServiceError


class BookNotFoundError(Exception):
    """Raised when a book is not found.

    :param book_id: ID of the book (optional)
    """

    def __init__(self, book_id: int | str | None = None) -> None:
        """Initialize BookNotFoundError.

        :param book_id: ID of the book (optional)
        :return: None
        """
        if book_id is not None:
            msg = f"No book found for id={book_id}"
        else:
            msg = "No book found"
        super().__init__(msg)


class BookAlreadyInLibraryError(Exception):
    """Raised when a user tries to add a book they already have."""

    def __init__(self, book_id: int) -> None:
        """Initialize the exception with the book ID."""
        self.book_id = book_id
        super().__init__(f"Book {book_id} is already in the library.")


class BookNotInLibraryError(Exception):
    """Raised when a user tries to remove a book they do not have."""

    def __init__(self, book_id: int) -> None:
        """Initialize the exception with the book ID."""
        self.book_id = book_id
        super().__init__(f"Book {book_id} is not in the library.")


class SelfFollowError(Exception):
    """Raised when a user attempts to follow themselves."""

    def __init__(self) -> None:
        """Initialize SelfFollowError."""
        super().__init__("Users cannot follow themselves.")


class SelfUnfollowError(Exception):
    """Raised when a user attempts to unfollow themselves."""

    def __init__(self) -> None:
        """Initialize SelfUnfollowError."""
        super().__init__("Users cannot unfollow themselves.")


class AlreadyFollowingError(Exception):
    """Raised when a user is already following another user."""

    def __init__(self) -> None:
        """Initialize AlreadyFollowingError."""
        super().__init__("User is already following this user.")


class PlaylistAlreadyExistsError(Exception):
    """Raised when a user already has a playlist with the same name.

    :param name: Name of the playlist that already exists
    """

    def __init__(self, name: str) -> None:
        """Initialize PlaylistAlreadyExistsError.

        :param name: Name of the playlist that already exists
        :return: None
        """
        super().__init__(f"Playlist {name} already exists")


class PlaylistNotFoundError(Exception):
    """Raised when a playlist does not exist or belongs to another user.

    :param id_playlist: ID of the playlist
    """

    def __init__(self, id_playlist: int) -> None:
        """Initialize PlaylistNotFoundError.

        :param id_playlist: ID of the playlist
        :return: None
        """
        super().__init__(f"No playlist found for id={id_playlist}")


class BookAlreadyInPlaylistError(Exception):
    """Raised when a book is already in a playlist.

    :param id_book: ID of the book
    """

    def __init__(self, id_book: int) -> None:
        """Initialize BookAlreadyInPlaylistError.

        :param id_book: ID of the book
        :return: None
        """
        super().__init__(f"Book {id_book} is already in the playlist")


class BookNotInPlaylistError(Exception):
    """Raised when a book is not in a playlist.

    :param id_book: ID of the book
    """

    def __init__(self, id_book: int) -> None:
        """Initialize BookNotInPlaylistError.

        :param id_book: ID of the book
        :return: None
        """
        super().__init__(f"Book {id_book} is not in the playlist")


class ReviewNotFoundError(Exception):
    """Raised when a review does not exist."""

    def __init__(self, review_id: int) -> None:
        """Initialize the exception with the review ID."""
        self.review_id = review_id
        super().__init__(f"No review found for id={review_id}")


class NotReviewAuthorError(Exception):
    """Raised when a user edits or deletes a review they did not write."""

    def __init__(self, review_id: int) -> None:
        """Initialize the exception with the review ID."""
        self.review_id = review_id
        super().__init__(f"User is not the author of review {review_id}.")


class ReviewAlreadyExistsError(Exception):
    """Raised when a user reviews the same book twice."""

    def __init__(self, book_id: int) -> None:
        """Initialize the exception with the book ID."""
        self.book_id = book_id
        super().__init__(f"Book {book_id} has already been reviewed.")


class NotFollowingError(Exception):
    """Raised when a user attempts to unfollow a user they do not follow."""

    def __init__(self) -> None:
        """Initialize NotFollowingError."""
        super().__init__("User is not following this user.")


class AccountBannedError(Exception):
    """Raised when a banned user logs in or uses a token."""

    def __init__(self) -> None:
        """Initialize AccountBannedError."""
        super().__init__("This account has been banned.")


class AccountSuspendedError(Exception):
    """Raised when a suspended user logs in or uses a token.

    :param until: End of the suspension
    """

    def __init__(self, until: datetime) -> None:
        """Initialize the exception with the end of the suspension."""
        self.until = until
        when = until.astimezone(UTC).strftime("%Y-%m-%d %H:%M")
        super().__init__(f"This account is suspended until {when} UTC.")


class SelfModerationError(Exception):
    """Raised when an admin tries to suspend or ban themself."""

    def __init__(self) -> None:
        """Initialize SelfModerationError."""
        super().__init__("Admins cannot moderate their own account.")


class AdminModerationError(Exception):
    """Raised when an admin tries to suspend or ban another admin."""

    def __init__(self) -> None:
        """Initialize AdminModerationError."""
        super().__init__("Admins cannot moderate another admin.")
