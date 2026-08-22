"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, routes

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(routes.router, tags=["routes"])
