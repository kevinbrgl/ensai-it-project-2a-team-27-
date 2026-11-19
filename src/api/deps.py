"""Dependencies for database access, services, and authentication.

FastAPI resolves these dependencies for each request.
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
from src.dao.achievements_dao import AchievementDAO
from src.dao.books_dao import BookDAO
from src.dao.genre_wheel_dao import GenreWheelDAO
from src.dao.library_dao import LibraryDAO
from src.dao.playlists_dao import PlaylistDAO
from src.dao.quests_dao import QuestDAO
from src.dao.recommendations_dao import RecommendationDAO
from src.dao.reviews_dao import ReviewDAO
from src.dao.stats_dao import StatsDAO
from src.dao.tokens_dao import TokenDAO
from src.dao.users_dao import UserDAO
from src.models import TokenPayload, User
from src.services.achievements_service import AchievementService
from src.services.admin_service import AdminService
from src.services.books_service import BookService
from src.services.genre_wheel_service import GenreWheelService
from src.services.library_service import LibraryService
from src.services.playlists_service import PlaylistService
from src.services.quests_service import QuestService
from src.services.recommendations_service import RecommendationService
from src.services.reviews_service import ReviewService
from src.services.stats_service import StatsService
from src.services.tokens_service import TokenService
from src.services.users_service import UserService
from src.utils.exceptions import (
    AccountBannedError,
    AccountSuspendedError,
    UserNotFoundError,
)

if TYPE_CHECKING:
    from psycopg2.pool import ThreadedConnectionPool

# rstrip: with ROOT_PATH="/", the URL must be "/api/...", not "//api/...",
# which the browser would read as a link to another host called "api".
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.ROOT_PATH.rstrip('/')}{settings.API_STR}/auth/login",
)


def get_cursor(request: Request) -> Generator[RealDictCursor]:
    """Yield a database cursor from the connection pool.

    Commit after a successful request and roll back on an exception.
    Return the connection to the pool when the request ends.

    Parameters
    ----------
    request : Request
        Request whose application owns the pool.

    Yields
    ------
    RealDictCursor
        Request-scoped cursor that returns rows as mappings.

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

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    UserService
        Service for user accounts and profiles.

    """
    return UserService(UserDAO(cursor))


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_token_service(cursor: CursorDep) -> TokenService:
    """Build a TokenService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    TokenService
        Service for access token revocation.

    """
    return TokenService(TokenDAO(cursor))


TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]


def get_user(
    service: UserServiceDep,
    tokens: TokenServiceDep,
    token: TokenDep,
) -> User:
    """Authenticate a user with a JWT bearer token.

    Parameters
    ----------
    service : UserService
        Service used to retrieve the account.
    tokens : TokenService
        Service used to check revocation.
    token : str
        JWT bearer token supplied with the request.

    Returns
    -------
    User
        Authenticated, active user.

    Raises
    ------
    HTTPException
        403 if the token is revoked or invalid, if its account no longer
        exists, or if the account is banned or suspended.

    """
    if tokens.is_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
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
        user = service.read(user_id=int(token_data.sub))

    # A token whose account was deleted is rejected like any invalid token.
    except (InvalidTokenError, ValidationError, UserNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    # A token issued before a ban or a suspension must stop working too.
    try:
        UserService.ensure_active(user)
    except (AccountBannedError, AccountSuspendedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from None
    return user


CurrentUser = Annotated[User, Depends(get_user)]


def get_admin_user(current_user: CurrentUser) -> User:
    """Require administrator rights on the authenticated account.

    Parameters
    ----------
    current_user : User
        Authenticated account to check.

    Returns
    -------
    User
        Authenticated administrator.

    Raises
    ------
    HTTPException
        403 if the account lacks administrator rights.

    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator rights required.",
        )
    return current_user


AdminUser = Annotated[User, Depends(get_admin_user)]


def get_book_service(cursor: CursorDep) -> BookService:
    """Build a BookService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    BookService
        Service for catalog operations and Open Library lookups.

    """
    return BookService(BookDAO(cursor))


BookServiceDep = Annotated[BookService, Depends(get_book_service)]


def get_library_service(cursor: CursorDep) -> LibraryService:
    """Build a LibraryService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    LibraryService
        Service for reading activity and library books.

    """
    return LibraryService(LibraryDAO(cursor))


LibraryServiceDep = Annotated[LibraryService, Depends(get_library_service)]


def get_playlist_service(cursor: CursorDep) -> PlaylistService:
    """Build a PlaylistService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    PlaylistService
        Service for playlists and their books.

    """
    return PlaylistService(PlaylistDAO(cursor))


PlaylistServiceDep = Annotated[PlaylistService, Depends(get_playlist_service)]


def get_review_service(cursor: CursorDep) -> ReviewService:
    """Build a ReviewService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    ReviewService
        Service for reviews and ratings.

    """
    return ReviewService(
        ReviewDAO(cursor),
        BookDAO(cursor),
        UserDAO(cursor),
        LibraryDAO(cursor),
    )


ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]


def get_quest_service(cursor: CursorDep) -> QuestService:
    """Build a QuestService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    QuestService
        Service for reading quests and their progress.

    """
    return QuestService(QuestDAO(cursor))


QuestServiceDep = Annotated[QuestService, Depends(get_quest_service)]


def get_genre_wheel_service(cursor: CursorDep) -> GenreWheelService:
    """Build a GenreWheelService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    GenreWheelService
        Service for genre proportions in an avatar ring.

    """
    return GenreWheelService(GenreWheelDAO(cursor))


GenreWheelServiceDep = Annotated[
    GenreWheelService,
    Depends(get_genre_wheel_service),
]


def get_achievement_service(cursor: CursorDep) -> AchievementService:
    """Build an AchievementService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    AchievementService
        Service for reading achievements and their progress.

    """
    return AchievementService(AchievementDAO(cursor))


AchievementServiceDep = Annotated[
    AchievementService,
    Depends(get_achievement_service),
]


def get_stats_service(cursor: CursorDep) -> StatsService:
    """Build a StatsService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    StatsService
        Service for reading statistics.

    """
    return StatsService(StatsDAO(cursor))


StatsServiceDep = Annotated[StatsService, Depends(get_stats_service)]


def get_recommendation_service(
    cursor: CursorDep,
    book_service: BookServiceDep,
) -> RecommendationService:
    """Build a RecommendationService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.
    book_service : BookService
        Catalog service using the same cursor.

    Returns
    -------
    RecommendationService
        Service for personalized book recommendations.

    """
    return RecommendationService(
        RecommendationDAO(cursor),
        StatsDAO(cursor),
        book_service,
    )


RecommendationServiceDep = Annotated[
    RecommendationService,
    Depends(get_recommendation_service),
]


def get_admin_service(cursor: CursorDep) -> AdminService:
    """Build an AdminService bound to the request cursor.

    Parameters
    ----------
    cursor : RealDictCursor
        Database cursor for the current request.

    Returns
    -------
    AdminService
        Service for account and review moderation.

    """
    return AdminService(UserDAO(cursor), ReviewDAO(cursor))


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
