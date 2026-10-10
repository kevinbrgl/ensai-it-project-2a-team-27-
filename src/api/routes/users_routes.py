"""Routes for user operations in the FastAPI application.

Provides endpoints for profile reading and updates.
Registration is handled in auth_routes.py.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser, CursorDep
from src.dao.users_dao import UserDAO
from src.models import (
    User,
    UserRead,
    UserUpdate,
    UserUpdatePassword,
)
from src.services.users_service import UserService
from src.utils.exceptions import (
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    SamePasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def read_self(current_user: CurrentUser) -> User:
    """Read the current users's information.

    :param current_user: The current authenticated user
    :return: The user information
    """
    return current_user


@router.patch("/me", response_model=UserRead)
def update_self(
    cursor: CursorDep, current_user: CurrentUser, user_in: UserUpdate,
) -> User:
    """Update the current user's information.

    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :param user_in: User update data
    :raises HTTPException: 400 if there is nothing to update,
        404 if the user is not found,
        409 if the new username or email is already used
    :return: The updated User object
    """
    try:
        return UserService(UserDAO(cursor)).update(
            current_user.id_user, user_in,
        )

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already used.",
        ) from None
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already used.",
        ) from None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nothing to update.",
        ) from None


@router.put("/me/password", response_model=UserRead)
def update_self_password(
    cursor: CursorDep, current_user: CurrentUser, user_in: UserUpdatePassword,
) -> User:
    """Update the current user's password.

    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :param user_in: Password update data
    :raises HTTPException: 400 if the new password is the same as the
     current one, 403 if the current password is wrong,
     404 if the user is not found    :return: The updated User object
    """
    try:
        return UserService(
            UserDAO(cursor),
        ).update_password(current_user, user_in)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None
    except SamePasswordError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new password must be different from the current one.",
        ) from None
    except IncorrectPasswordError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wrong password provided",
        ) from None
