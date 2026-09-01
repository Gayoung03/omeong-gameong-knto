"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    chatbot,
    checklists,
    guides,
    health,
    memos,
    notices,
    notifications,
    pets,
    places,
    reviews,
    route_items,
    routes,
    travel_logs,
    uploads,
    users,
    weather,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(routes.router, tags=["routes"])
api_router.include_router(route_items.router, tags=["routes"])
api_router.include_router(checklists.router, tags=["routes"])
api_router.include_router(memos.router, tags=["routes"])
api_router.include_router(notifications.router, tags=["notifications"])
api_router.include_router(notices.router, tags=["notices"])
api_router.include_router(places.router, tags=["places"])
api_router.include_router(reviews.router, tags=["reviews"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(pets.router, tags=["pets"])
api_router.include_router(travel_logs.router, tags=["travel-logs"])
api_router.include_router(uploads.router, tags=["uploads"])
api_router.include_router(weather.router, tags=["weather"])
api_router.include_router(chatbot.router, tags=["chat"])
api_router.include_router(guides.router, tags=["guides"])
