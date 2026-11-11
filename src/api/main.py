"""Main API router configuration for FastAPI."""

from fastapi import APIRouter

from src.api.routes import (
    admin_routes,
    auth_routes,
    books_routes,
    library_routes,
    playlists_routes,
    recommendations_routes,
    reviews_routes,
    users_routes,
)
from src.core.config import settings

api_router = APIRouter(prefix=settings.API_STR)

api_router.include_router(auth_routes.router)
api_router.include_router(books_routes.router)
api_router.include_router(users_routes.router)
api_router.include_router(library_routes.router)
api_router.include_router(playlists_routes.router)
api_router.include_router(reviews_routes.router)
api_router.include_router(recommendations_routes.router)
api_router.include_router(admin_routes.router)
