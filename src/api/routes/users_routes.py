"""Routes for user operations in the FastAPI application.

Provides endpoints for user registration, profile reading, and updates.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser, CursorDep
from src.dao.users_dao import UserDAO
from src.models import (
    User,
    UserRead,
    UserRegister,
    UserUpdate,
    UserUpdatePassword,
)
from src.services.users_service import UserService
from src.utils.exceptions import (
    DAOError,
    IncorrectPasswordError,
    SamePasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/signup",
             response_model=UserRead,
             status_code=status.HTTP_201_CREATED)
def register(cursor: CursorDep, user_in: UserRegister) -> User:
    """Register a new user.

    :param cursor: Database cursor dependency
    :param user_in: User registration data
    :raises HTTPException: Raised if user already exists or registration fails
    :return: The created User object
    """
    service = UserService(UserDAO(cursor))
    try:
        return service.register(user_in)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        ) from None
    except DAOError:  # Ok faudra vraiment faire un truc c'est éclaté
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not register user.",
        ) from None


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
    :raises HTTPException: Raised if user not found
    :return: The updated User object
    """
    try:
        return UserService(UserDAO(cursor)).update(current_user.id, user_in)

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from None


@router.patch("/me/password", response_model=UserRead)
def update_self_password(
    cursor: CursorDep, current_user: CurrentUser, user_in: UserUpdatePassword,
) -> User:
    """Update the current user's password.

    :param cursor: Database cursor dependency
    :param current_user: The current authenticated user
    :param user_in: Password update data
    :raises HTTPException: Raised if user not found, or password error
    :return: The updated User object
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The new password must be different from the current one.",
        ) from None
    except IncorrectPasswordError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wrong password provided",
        ) from None
