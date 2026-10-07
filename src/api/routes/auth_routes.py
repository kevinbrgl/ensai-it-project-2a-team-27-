"""Routes for authentication in the FastAPI application.

Provides the endpoint for account registration.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from src.api.deps import UserServiceDep
from src.models import User, UserRead, UserRegister
from src.utils.exceptions import (
    DAOError,
    EmailAlreadyExistsError,
    UserAlreadyExistsError,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post("/register",
             response_model=UserRead,
             status_code=status.HTTP_201_CREATED)
def register(service: UserServiceDep, user_in: UserRegister) -> User:
    """Register a new user.

    :param service: User service dependency
    :param user_in: User registration data (username, email, password)
    :raises HTTPException: 409 if the username or email is already used,
        500 if the registration fails
    :return: The created user (without the password hash)
    """
    try:
        return service.register(user_in)
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
    except DAOError:
        logger.exception("Registration failed for username=%s",
                         user_in.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not register user.",
        ) from None
