"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    checklists,
    health,
    memos,
    places,
    reviews,
    route_items,
    routes,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(routes.router, tags=["routes"])
api_router.include_router(route_items.router, tags=["routes"])
api_router.include_router(checklists.router, tags=["routes"])
api_router.include_router(memos.router, tags=["routes"])
api_router.include_router(places.router, tags=["places"])
api_router.include_router(reviews.router, tags=["reviews"])
