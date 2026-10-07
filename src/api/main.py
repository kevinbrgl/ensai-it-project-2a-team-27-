"""Main API router configuration for FastAPI."""

from fastapi import APIRouter

from api.routes import auth_routes, login_routes, users_routes
from core.config import settings

api_router = APIRouter(prefix=settings.API_STR)

api_router.include_router(auth_routes.router)
api_router.include_router(login_routes.router)
api_router.include_router(users_routes.router)
