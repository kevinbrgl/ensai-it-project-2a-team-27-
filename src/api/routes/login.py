"""Login route for obtaining access tokens."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.api.deps import CursorDep
from src.core import security
from src.core.config import settings
from src.dao.users import UserDAO
from src.models import Token
from src.services.users import UserService
from src.utils.exceptions import AuthError

router = APIRouter(tags=["Login"])


@router.post("/login/access-token")
def login_access_token(
    cur: CursorDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Authenticate user and return an access token.

    :param cur: Database cursor dependency
    :param form_data: OAuth2 password request form
    :raises HTTPException: Raised if authentication fails
    :return: Token object with access token and type
    """
    try:
        user = UserService(UserDAO(cur)).authenticate(
            username=form_data.username, password=form_data.password,
        )
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            user.id, expires_delta=access_token_expires,
        )
        return Token(access_token=access_token, token_type=settings.TOKEN_TYPE)
    except AuthError:
        raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            ) from None
