"""Main API router configuration for FastAPI."""

from fastapi import APIRouter

from api.routes import login_routes, users_routes, items_routes
from core.config import settings

api_router = APIRouter(prefix=settings.API_STR)

api_router.include_router(login_routes.router)
api_router.include_router(users_routes.router)
api_router.include_router(items_routes.router)
