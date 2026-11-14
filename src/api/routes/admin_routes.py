"""Admin moderation routes: suspend, ban, remove reviews."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from src.api.deps import AdminServiceDep, AdminUser
from src.models.admin import ModerationStatus, SuspendRequest
from src.utils.exceptions import (
    AdminModerationError,
    DAOError,
    ReviewNotFoundError,
    SelfModerationError,
    UserNotFoundError,
)

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)

UserId = Annotated[int, Path(ge=1, description="Database ID of the user")]
ReviewId = Annotated[int, Path(ge=1, description="Database ID of the review")]


def _moderation_error(exc: Exception) -> HTTPException:
    """Translate a moderation exception into an HTTP error."""
    if isinstance(exc, SelfModerationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot moderate your own account.",
        )
    if isinstance(exc, AdminModerationError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot moderate another admin.",
        )
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found.",
    )


@router.post(
    "/users/{user_id}/suspend",
    summary="⏸️ Suspend a user",
    responses={
        400: {"description": "You cannot moderate your own account"},
        403: {"description": "Not an admin, or the target is an admin"},
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def suspend_user(
    user_id: UserId,
    suspension: SuspendRequest,
    service: AdminServiceDep,
    admin: AdminUser,
) -> ModerationStatus:
    """**Temporarily suspend** a user account.

    🛡️ Admin only

    **Field:** `days`, the length of the suspension, from **1** to
    **365** days.

    **Behaviour:** until the end of the suspension, the user cannot
    **log in** nor use their **existing tokens**.

    **Rules:**

    - You cannot suspend **yourself**
    - You cannot suspend **another admin**

    **Example request:**

    ```json
    {
      "days": 7
    }
    ```
    \f
    :param user_id: ID of the user to suspend
    :param suspension: Length of the suspension in days
    :param service: Admin service dependency
    :param admin: The authenticated admin
    :raises HTTPException: 400 if the admin targets themself,
        403 if not admin or if the target is an admin,
        404 if the user does not exist, 500 on database error
    :return: The new moderation status of the user
    """
    try:
        return service.suspend_user(
            admin.id_user,
            user_id,
            suspension.days,
        )
    except (
        SelfModerationError,
        AdminModerationError,
        UserNotFoundError,
    ) as exc:
        raise _moderation_error(exc) from None
    except DAOError:
        logger.exception("Failed to suspend user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not suspend the user.",
        ) from None


@router.post(
    "/users/{user_id}/ban",
    summary="⛔ Ban a user",
    responses={
        400: {"description": "You cannot moderate your own account"},
        403: {"description": "Not an admin, or the target is an admin"},
        404: {"description": "User not found"},
        500: {"description": "Database error"},
    },
)
def ban_user(
    user_id: UserId,
    service: AdminServiceDep,
    admin: AdminUser,
) -> ModerationStatus:
    """**Permanently ban** a user account.

    🛡️ Admin only

    **Behaviour:** the user can no longer **log in** nor use their
    **existing tokens**. Unlike a suspension, a ban has **no end
    date**.

    **Rules:**

    - You cannot ban **yourself**
    - You cannot ban **another admin**

    **Returns:** the new moderation status of the user
    (`is_banned`, `suspended_until`).
    \f
    :param user_id: ID of the user to ban
    :param service: Admin service dependency
    :param admin: The authenticated admin
    :raises HTTPException: 400 if the admin targets themself,
        403 if not admin or if the target is an admin,
        404 if the user does not exist, 500 on database error
    :return: The new moderation status of the user
    """
    try:
        return service.ban_user(admin.id_user, user_id)
    except (
        SelfModerationError,
        AdminModerationError,
        UserNotFoundError,
    ) as exc:
        raise _moderation_error(exc) from None
    except DAOError:
        logger.exception("Failed to ban user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not ban the user.",
        ) from None


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="🗑️ Remove a review",
    responses={
        403: {"description": "Administrator rights required"},
        404: {"description": "Review not found"},
        500: {"description": "Database error"},
    },
)
def moderate_review(
    review_id: ReviewId,
    service: AdminServiceDep,
    _admin: AdminUser,
) -> None:
    """Remove **any review**, whoever wrote it.

    🛡️ Admin only

    **Use case:** moderate a review that is offensive or off topic.

    **Response:** `204 No Content`, with an empty body.
    \f
    :param review_id: ID of the review
    :param service: Admin service dependency
    :param _admin: The authenticated admin
    :raises HTTPException: 403 if not admin, 404 if the review does not
        exist, 500 on database error
    """
    try:
        service.delete_review(review_id)
    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found.",
        ) from None
    except DAOError:
        logger.exception("Failed to moderate review %s", review_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not remove the review.",
        ) from None
