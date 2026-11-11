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
    """Build the moderation status of a user."""
    return ModerationStatus(
        id_user=user.id_user,
        username=user.username,
        is_banned=user.is_banned,
        suspended_until=user.suspended_until,
    )


class AdminService:
    """Service class for the moderation actions of administrators."""

    def __init__(self, user_dao: UserDAO, review_dao: ReviewDAO) -> None:
        """Initialize the service with its DAOs.

        :param user_dao: The user data access object
        :param review_dao: The review data access object
        """
        self.user_dao = user_dao
        self.review_dao = review_dao

    def _check_target(self, admin_id: int, user_id: int) -> None:
        """Make sure the target user can be moderated by this admin.

        :param admin_id: ID of the admin making the request
        :param user_id: ID of the targeted user
        :raises SelfModerationError: If the admin targets themself
        :raises UserNotFoundError: If the target does not exist
        :raises AdminModerationError: If the target is an admin
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

        :param admin_id: ID of the admin making the request
        :param user_id: ID of the user to suspend
        :param days: Length of the suspension in days
        :return: The new moderation status of the user
        """
        self._check_target(admin_id, user_id)
        until = datetime.now(UTC) + timedelta(days=days)
        user = self.user_dao.set_suspended_until(user_id, until)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return _to_status(user)

    def ban_user(self, admin_id: int, user_id: int) -> ModerationStatus:
        """Permanently ban an account.

        :param admin_id: ID of the admin making the request
        :param user_id: ID of the user to ban
        :return: The new moderation status of the user
        """
        self._check_target(admin_id, user_id)
        user = self.user_dao.set_banned(user_id, banned=True)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return _to_status(user)

    def delete_review(self, review_id: int) -> None:
        """Remove any review.

        :param review_id: ID of the review
        :raises ReviewNotFoundError: If the review does not exist
        """
        self.review_dao.delete(review_id)
