"""Database metadata regression tests."""

from app.db import models  # noqa: F401
from app.db.base import Base

EXPECTED_TABLES = {
    "chat_conversations",
    "chat_messages",
    "favorites",
    "inquiries",
    "notices",
    "notifications",
    "pets",
    "place_business_hours",
    "place_external_refs",
    "place_pet_policies",
    "place_tag_links",
    "place_tags",
    "places",
    "review_images",
    "reviews",
    "route_calculation_cache",
    "route_checklist_items",
    "route_days",
    "route_items",
    "route_memos",
    "route_moves",
    "route_request_pets",
    "route_request_stays",
    "route_requests",
    "routes",
    "travel_log_pets",
    "travel_logs",
    "user_travel_preferences",
    "users",
    "weather_snapshots",
}


def test_all_documented_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES
