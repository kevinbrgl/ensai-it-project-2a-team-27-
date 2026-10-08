"""Dependency injection utilities for FastAPI routes.

Provides database cursor, service, token, and user authentication
dependencies.
"""

from collections.abc import Generator
from typing import TYPE_CHECKING, Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from psycopg2.extras import RealDictCursor
from pydantic import ValidationError

from src.core import security
from src.core.config import settings
from src.dao.users_dao import UserDAO
from src.models import TokenPayload, User
from src.services.users_service import UserService
from src.utils.exceptions import UserNotFoundError

if TYPE_CHECKING:
    from psycopg2.pool import ThreadedConnectionPool

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.ROOT_PATH}{settings.API_STR}/auth/login",
)


def get_cursor(request: Request) -> Generator[RealDictCursor]:
    """Yield a database cursor from the connection pool.

    Commit if the request succeeds, rollback otherwise, then give
    the connection back to the pool.

    :param request: FastAPI request object
    :return: Generator yielding a RealDictCursor
    """
    pool: ThreadedConnectionPool = request.app.state.db_pool
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


CursorDep = Annotated[RealDictCursor, Depends(get_cursor)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_user_service(cursor: CursorDep) -> UserService:
    """Build a UserService bound to the request cursor.

    :param cursor: Database cursor dependency
    :return: A UserService instance
    """
    return UserService(UserDAO(cursor))


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_user(service: UserServiceDep, token: TokenDep) -> User:
    """Retrieve the current user from a JWT token.

    :param service: User service dependency
    :param token: JWT token dependency
    :raises HTTPException: Raised if credentials are invalid or user not found
    :return: The authenticated User object
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[security.ALGORITHM],
        )
        token_data = TokenPayload.model_validate(payload)
        if not token_data.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return service.read(user_id=int(token_data.sub))

    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such user in database",
        ) from None  # Should i use a 404 ? I mean it's auth


CurrentUser = Annotated[User, Depends(get_user)]
