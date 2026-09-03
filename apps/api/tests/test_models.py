"""Database metadata regression tests."""

from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.enums import RouteCreationType

EXPECTED_TABLES = {
    "chat_conversations",
    "chat_messages",
    "favorites",
    "guide_document_sources",
    "guide_documents",
    "inquiries",
    "notices",
    "notifications",
    "password_reset_codes",
    "password_reset_requests",
    "pets",
    "place_business_hours",
    "place_external_refs",
    "place_pet_policies",
    "place_tag_links",
    "place_tags",
    "places",
    "push_tokens",
    "review_images",
    "reviews",
    "route_calculation_cache",
    "route_checklist_items",
    "route_days",
    "route_items",
    "route_memos",
    "route_moves",
    "route_pets",
    "route_request_pets",
    "route_request_stays",
    "route_requests",
    "routes",
    "transport_pet_rules",
    "transport_restricted_breeds",
    "travel_log_pets",
    "travel_logs",
    "user_consents",
    "user_social_accounts",
    "user_travel_preferences",
    "users",
    "weather_snapshots",
}


def test_all_documented_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_user_consent_schema() -> None:
    consents = Base.metadata.tables["user_consents"]

    # 동의 이력은 쌓기만 하므로 갱신 시각 컬럼을 두지 않는다.
    assert set(consents.c.keys()) == {
        "id",
        "user_id",
        "consent_type",
        "is_agreed",
        "document_version",
        "created_at",
    }
    # 문서가 없는 age_14_or_over 동의는 버전을 비워 둔다.
    assert consents.c.document_version.nullable is True
    assert consents.c.is_agreed.nullable is False


def test_pet_species_detail_schema() -> None:
    pets = Base.metadata.tables["pets"]
    species_detail = pets.c.species_detail

    assert species_detail.nullable is True
    assert species_detail.type.length == 50
    assert any(
        constraint.name == "ck_pets_species_detail_consistency"
        for constraint in pets.constraints
        if isinstance(constraint, CheckConstraint)
    )


def test_manual_route_schema() -> None:
    routes = Base.metadata.tables["routes"]
    route_pets = Base.metadata.tables["route_pets"]

    assert routes.c.route_request_id.nullable is True
    assert routes.c.creation_type.nullable is False
    assert routes.c.creation_type.type.enums == [member.value for member in RouteCreationType]
    assert any(
        constraint.name == "ck_routes_creation_type_request_consistency"
        for constraint in routes.constraints
        if isinstance(constraint, CheckConstraint)
    )
    assert {column.name for column in route_pets.primary_key.columns} == {"route_id", "pet_id"}


def test_unverifiable_place_scores_are_removed() -> None:
    places = Base.metadata.tables["places"]

    assert not {
        "activity_level",
        "crowd_level",
        "weather_sensitivity",
    }.intersection(places.c.keys())


def test_route_request_stores_applied_weight_snapshot() -> None:
    route_requests = Base.metadata.tables["route_requests"]

    assert route_requests.c.priority_preset.type.length == 30
    assert isinstance(route_requests.c.applied_weights.type, JSONB)
    assert route_requests.c.priority_preset.nullable is True
    assert route_requests.c.applied_weights.nullable is True
