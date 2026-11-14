"""Routes for authentication in the FastAPI application.

Provides the endpoints for account registration and login.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.api.deps import (
    CurrentUser,
    TokenDep,
    TokenServiceDep,
    UserServiceDep,
)
from src.models import Token, User, UserRead, UserRegister
from src.utils.exceptions import (
    AccountBannedError,
    AccountSuspendedError,
    AuthError,
    DAOError,
    EmailAlreadyExistsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="📝 Create an account",
    responses={
        409: {"description": "Username or email already used"},
        500: {"description": "Database error"},
    },
)
def register(service: UserServiceDep, user_in: UserRegister) -> User:
    """Create a new **user account**.

    🔓 Public route, no authentication needed

    **Rules:**

    - 👤 `username`: 3 to 30 characters, must be **unique**
    - 📧 `email`: a valid address, must be **unique**
    - 🔑 `password`: 8 to 72 characters

    **Good to know:** the password is never returned by the API.

    **Example request:**

    ```json
    {
      "username": "alice",
      "email": "alice@example.com",
      "password": "my-secret-password"
    }
    ```
    \f
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
        logger.exception(
            "Registration failed for username=%s",
            user_in.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not register user.",
        ) from None


@router.post(
    "/login",
    summary="🔑 Log in",
    responses={
        401: {"description": "Incorrect username or password"},
        403: {"description": "Account banned or suspended"},
        500: {"description": "Database error"},
    },
)
def login(
    service: UserServiceDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Log in and get an **access token**.

    🔓 Public route, no authentication needed

    **How to use it:**

    - Send `username` and `password` as **form data** (not JSON)
    - Put the returned `access_token` in the header
      `Authorization: Bearer <token>` of your next requests

    **In this page:** the **Authorize** button (top right) does it
    for you.

    **Access refused:** a **banned** or **suspended** account cannot
    log in.
    \f
    :param service: User service dependency
    :param form_data: Login form (username and password fields)
    :raises HTTPException: 401 if the username or password is incorrect,
        403 if the account is banned or suspended, 500 if the login fails
    :return: The access token and its type
    """
    try:
        return service.login(form_data.username, form_data.password)
    except (UserNotFoundError, AuthError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except (AccountBannedError, AccountSuspendedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from None
    except DAOError:
        logger.exception("Login failed for username=%s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not log in.",
        ) from None


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="🚪 Log out",
    responses={500: {"description": "Database error"}},
)
def logout(
    service: TokenServiceDep,
    token: TokenDep,
    _current_user: CurrentUser,
) -> None:
    """Log out by **revoking** the current access token.

    🔒 Authentication required

    **Behaviour:** once revoked, the token is **rejected** on every
    protected route. Log in again to get a new one.

    **Response:** `204 No Content`, with an empty body.
    \f
    :param service: Token service dependency
    :param token: The token sent with the request
    :param _current_user: The authenticated user (checks the token)
    :raises HTTPException: 500 if the revocation fails
    """
    try:
        service.revoke(token)
    except DAOError:
        logger.exception("Logout failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not log out.",
        ) from None
