"""Service layer for admin moderation (suspend, ban, remove reviews)."""

from datetime import UTC, datetime, timedelta

from src.dao.reviews_dao import ReviewDAO
from src.dao.users_dao import UserDAO
from src.models.admin import ModerationStatus
from src.models.users import User
from src.utils.exceptions import (
    AdminModerationError,
    SelfModerationError,
    UserNotFoundError,
)


def _to_status(user: User) -> ModerationStatus:
    """Build the moderation status of a user.

    Parameters
    ----------
    user : User
        Account whose moderation status is needed.

    Returns
    -------
    ModerationStatus
        The user ID, username, ban flag and suspension end time.

    """
    return ModerationStatus(
        id_user=user.id_user,
        username=user.username,
        is_banned=user.is_banned,
        suspended_until=user.suspended_until,
    )


class AdminService:
    """Suspend and ban accounts and remove reviews."""

    def __init__(self, user_dao: UserDAO, review_dao: ReviewDAO) -> None:
        """Initialize the service with its DAOs.

        Parameters
        ----------
        user_dao : UserDAO
            The user data access object.
        review_dao : ReviewDAO
            The review data access object.

        """
        self.user_dao = user_dao
        self.review_dao = review_dao

    def _check_target(self, admin_id: int, user_id: int) -> None:
        """Validate the target of an administrator's moderation action.

        Parameters
        ----------
        admin_id : int
            ID of the admin making the request.
        user_id : int
            ID of the targeted user.

        Raises
        ------
        SelfModerationError
            If the administrator targets their own account.
        UserNotFoundError
            If the target account does not exist.
        AdminModerationError
            If the target is another administrator.

        """
        if admin_id == user_id:
            raise SelfModerationError
        target = self.user_dao.read(user_id)
        if target is None:
            raise UserNotFoundError(user_id=user_id)
        if target.is_admin:
            raise AdminModerationError

    def suspend_user(
        self,
        admin_id: int,
        user_id: int,
        days: int,
    ) -> ModerationStatus:
        """Suspend an account for a number of days.

        Parameters
        ----------
        admin_id : int
            ID of the admin making the request.
        user_id : int
            ID of the user to suspend.
        days : int
            Length of the suspension in days.

        Returns
        -------
        ModerationStatus
            The new moderation status of the user.

        Raises
        ------
        UserNotFoundError
            If the target account does not exist.

        Notes
        -----
        Targeting one's own account raises ``SelfModerationError``. Targeting
        another administrator raises ``AdminModerationError``.

        """
        self._check_target(admin_id, user_id)
        until = datetime.now(UTC) + timedelta(days=days)
        user = self.user_dao.set_suspended_until(user_id, until)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return _to_status(user)

    def ban_user(self, admin_id: int, user_id: int) -> ModerationStatus:
        """Permanently ban an account.

        Parameters
        ----------
        admin_id : int
            ID of the admin making the request.
        user_id : int
            ID of the user to ban.

        Returns
        -------
        ModerationStatus
            The new moderation status of the user.

        Raises
        ------
        UserNotFoundError
            If the target account does not exist.

        Notes
        -----
        Targeting one's own account raises ``SelfModerationError``. Targeting
        another administrator raises ``AdminModerationError``.

        """
        self._check_target(admin_id, user_id)
        user = self.user_dao.set_banned(user_id, banned=True)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return _to_status(user)

    def delete_review(self, review_id: int) -> None:
        """Remove any review.

        Parameters
        ----------
        review_id : int
            ID of the review.

        Notes
        -----
        A missing review raises ``ReviewNotFoundError``.

        """
        self.review_dao.delete(review_id)
