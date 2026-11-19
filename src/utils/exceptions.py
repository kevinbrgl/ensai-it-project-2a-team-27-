"""Custom exception classes for application errors.

Defines exceptions for user, item, authentication, and DAO errors.
"""

from datetime import UTC, datetime


class UserNotFoundError(Exception):
    """Raised when a user is not found."""

    def __init__(
        self,
        user_id: int | None = None,
        username: str | None = None,
    ) -> None:
        """Initialize the error for a missing user.

        Parameters
        ----------
        user_id : int | None, optional
            Database ID of the user. Takes priority when provided.
        username : str | None, optional
            Username used when no ID is supplied.

        """
        if user_id:
            msg = f"No user found for id={user_id}"
        elif username:
            msg = f"No user found for username='{username}'"
        else:
            msg = "No user found"
        super().__init__(msg)


class DAOError(Exception):
    """Raised for errors in the Data Access Object (DAO) layer."""

    def __init__(self, message: str | None = None) -> None:
        """Initialize the error raised by a DAO.

        Parameters
        ----------
        message : str | None, optional
            Custom error message. Uses a generic DAO message by default.

        """
        if message is None:
            message = "Something went wrong in the DAO."
        super().__init__(message)


class AuthError(Exception):
    """Raised for authentication errors."""

    def __init__(self) -> None:
        """Initialize the error for credentials that could not be validated."""
        super().__init__("Could not validate credentials")


class IncorrectPasswordError(Exception):
    """Raised when an incorrect password is provided."""

    def __init__(self) -> None:
        """Initialize the error for an incorrect password."""
        super().__init__("Incorrect password provided")


class SamePasswordError(Exception):
    """Raised when the new password is the same as the old password."""

    def __init__(self) -> None:
        """Initialize the error for reusing the current password."""
        super().__init__("New password must be different from the old one.")


class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an existing username."""

    def __init__(self, username: str) -> None:
        """Initialize the error for a duplicate username.

        Parameters
        ----------
        username : str
            Username that is already registered.

        """
        super().__init__(f"Username {username} already exists")


class EmailAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an existing email."""

    def __init__(self, email: str) -> None:
        """Initialize the error for a duplicate email address.

        Parameters
        ----------
        email : str
            Email address that is already registered.

        """
        super().__init__(f"Email {email} already exists")


class ExternalServiceError(Exception):
    """Raised when an external service is unavailable."""

    def __init__(self, message: str | None = None) -> None:
        """Initialize the error raised for an unavailable external service.

        Parameters
        ----------
        message : str | None, optional
            Custom error message. Uses a generic message by default.

        """
        if message is None:
            message = "External service is currently unavailable."
        super().__init__(message)


ExternalServiceException = ExternalServiceError


class InvalidSearchQueryError(ExternalServiceError):
    """Raised when Open Library rejects a search query as invalid.

    Open Library answers HTTP 422 for queries made only of stopwords such as
    "the" or "a". This subclasses ``ExternalServiceError`` so callers that
    only handle the generic error keep working.
    """

    def __init__(self, message: str | None = None) -> None:
        """Initialize the error for a query rejected by Open Library.

        Parameters
        ----------
        message : str | None, optional
            Custom error message. Uses a generic message by default.

        """
        if message is None:
            message = "Search is too generic, add more words."
        super().__init__(message)


class BookNotFoundError(Exception):
    """Raised when a book is not found."""

    def __init__(self, book_id: int | str | None = None) -> None:
        """Initialize the error for a missing book.

        Parameters
        ----------
        book_id : int | str | None, optional
            Book identifier to include in the error message.

        """
        if book_id is not None:
            msg = f"No book found for id={book_id}"
        else:
            msg = "No book found"
        super().__init__(msg)


class BookAlreadyInLibraryError(Exception):
    """Raised when a user tries to add a book they already have."""

    def __init__(self, book_id: int) -> None:
        """Initialize the error for an existing library entry.

        Parameters
        ----------
        book_id : int
            ID of the book already in the library.

        """
        self.book_id = book_id
        super().__init__(f"Book {book_id} is already in the library.")


class BookNotInLibraryError(Exception):
    """Raised when a user tries to remove a book they do not have."""

    def __init__(self, book_id: int) -> None:
        """Initialize the error for a missing library entry.

        Parameters
        ----------
        book_id : int
            ID of the book absent from the library.

        """
        self.book_id = book_id
        super().__init__(f"Book {book_id} is not in the library.")


class InvalidReadingDatesError(Exception):
    """Raised when a reading end date is before the start date."""

    def __init__(self) -> None:
        """Initialize InvalidReadingDatesError."""
        super().__init__("The end date cannot be before the start date.")


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
    """Raised when a user already has a playlist with the same name."""

    def __init__(self, name: str) -> None:
        """Initialize the error for a duplicate playlist name.

        Parameters
        ----------
        name : str
            Playlist name that the user already has.

        """
        super().__init__(f"Playlist {name} already exists")


class PlaylistNotFoundError(Exception):
    """Raised when a playlist does not exist or belongs to another user."""

    def __init__(self, id_playlist: int) -> None:
        """Initialize the error for an unavailable playlist.

        Parameters
        ----------
        id_playlist : int
            ID of the requested playlist.

        """
        super().__init__(f"No playlist found for id={id_playlist}")


class BookAlreadyInPlaylistError(Exception):
    """Raised when a book is already in a playlist."""

    def __init__(self, id_book: int) -> None:
        """Initialize the error for an existing playlist entry.

        Parameters
        ----------
        id_book : int
            ID of the book already in the playlist.

        """
        super().__init__(f"Book {id_book} is already in the playlist")


class BookNotInPlaylistError(Exception):
    """Raised when a book is not in a playlist."""

    def __init__(self, id_book: int) -> None:
        """Initialize the error for a missing playlist entry.

        Parameters
        ----------
        id_book : int
            ID of the book absent from the playlist.

        """
        super().__init__(f"Book {id_book} is not in the playlist")


class ReviewNotFoundError(Exception):
    """Raised when a review does not exist."""

    def __init__(self, review_id: int) -> None:
        """Initialize the error for a missing review.

        Parameters
        ----------
        review_id : int
            ID of the requested review.

        """
        self.review_id = review_id
        super().__init__(f"No review found for id={review_id}")


class NotReviewAuthorError(Exception):
    """Raised when a user edits or deletes a review they did not write."""

    def __init__(self, review_id: int) -> None:
        """Initialize the error for an action restricted to the review author.

        Parameters
        ----------
        review_id : int
            ID of the review the user tried to edit or delete.

        """
        self.review_id = review_id
        super().__init__(f"User is not the author of review {review_id}.")


class ReviewAlreadyExistsError(Exception):
    """Raised when a user reviews the same book twice."""

    def __init__(self, book_id: int) -> None:
        """Initialize the error for a duplicate book review.

        Parameters
        ----------
        book_id : int
            ID of the book the user has already reviewed.

        """
        self.book_id = book_id
        super().__init__(f"Book {book_id} has already been reviewed.")


class NotFollowingError(Exception):
    """Raised when a user attempts to unfollow a user they do not follow."""

    def __init__(self) -> None:
        """Initialize NotFollowingError."""
        super().__init__("User is not following this user.")


class PrivateProfileError(Exception):
    """Raised when another user's private library or activity is read."""

    def __init__(self) -> None:
        """Initialize PrivateProfileError."""
        super().__init__("This profile is private.")


class AccountBannedError(Exception):
    """Raised when a banned user logs in or uses a token."""

    def __init__(self) -> None:
        """Initialize AccountBannedError."""
        super().__init__("This account has been banned.")


class AccountSuspendedError(Exception):
    """Raised when a suspended user logs in or uses a token."""

    def __init__(self, until: datetime) -> None:
        """Initialize the error with the suspension end time in UTC.

        Parameters
        ----------
        until : datetime
            Time at which the suspension ends.

        """
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
