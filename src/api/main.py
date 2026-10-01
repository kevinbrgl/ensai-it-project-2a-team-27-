"""Main API router configuration for FastAPI."""

from fastapi import APIRouter

from api.routes import items, login, users
from core.config import settings

api_router = APIRouter(prefix=settings.API_STR)

api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(items.router)
