from decimal import Decimal

import pytest

from app.db.models.enums import DataProvider, PetPolicyType
from app.integrations.maps.kakao import GeocodedAddress
from scripts.seed_landmarks import (
    ExistingPlace,
    duplicate_reason,
    policy_column_values,
    resolve_coord,
    validate,
    validate_updates,
)

VALID_TAGS = frozenset(
    {"sea", "cafe", "walk", "photo_spot", "experience", "rest", "indoor_tourism"}
)


def _item(**overrides: object) -> dict:
    base = {
        "name": "섭지코지",
        "category": "attraction",
        "region": "표선/성산",
        "address": "제주특별자치도 서귀포시 성산읍 고성리 87",
        "latitude": 33.4241,
        "longitude": 126.9296,
        "tags": ["sea", "walk", "photo_spot"],
        "pet_policy": {"policy_type": "outdoor_only", "source_url": "https://example.com"},
    }
    base.update(overrides)
    return base


# --- 검증: 하나라도 실패하면 전체 거부 ---------------------------------------


def test_valid_item_passes() -> None:
    assert validate([_item()], VALID_TAGS) == []


def test_missing_source_url_is_rejected() -> None:
    errors = validate([_item(pet_policy={"policy_type": "outdoor_only"})], VALID_TAGS)
    assert any("source_url" in error.reason for error in errors)


def test_policy_type_outside_enum_is_rejected() -> None:
    errors = validate(
        [_item(pet_policy={"policy_type": "sometimes", "source_url": "https://x"})], VALID_TAGS
    )
    assert any("policy_type" in error.reason for error in errors)


def test_unknown_tag_is_rejected() -> None:
    errors = validate([_item(tags=["sea", "바다"])], VALID_TAGS)
    assert any("태그" in error.reason for error in errors)


def test_region_outside_db_values_is_rejected() -> None:
    errors = validate([_item(region="제주 동부")], VALID_TAGS)
    assert any("region" in error.reason for error in errors)


def test_category_outside_allowed_is_rejected() -> None:
    errors = validate([_item(category="cafe")], VALID_TAGS)
    assert any("category" in error.reason for error in errors)


# --- 멱등: 이름·100m 중복 ----------------------------------------------------


def test_duplicate_by_name() -> None:
    existing = [ExistingPlace("섭지코지", (33.0, 126.0), True)]
    assert duplicate_reason("섭지코지", (35.0, 127.0), existing) is not None


def test_duplicate_by_distance_within_100m() -> None:
    existing = [ExistingPlace("가까운 다른 이름", (33.4241, 126.9296), True)]
    assert duplicate_reason("섭지코지", (33.4242, 126.9297), existing) is not None


def test_not_duplicate_when_far_and_different_name() -> None:
    existing = [ExistingPlace("먼 다른 이름", (34.0, 127.0), True)]
    assert duplicate_reason("섭지코지", (33.4241, 126.9296), existing) is None


def test_inactive_place_does_not_block_by_distance() -> None:
    # 이름이 다르고 비활성이면 같은 좌표라도 100m 규칙에 걸리지 않는다.
    existing = [ExistingPlace("비활성 장소", (33.4241, 126.9296), False)]
    assert duplicate_reason("섭지코지", (33.4241, 126.9296), existing) is None


# --- 지오코딩 폴백 -----------------------------------------------------------


def test_geocode_fallback_when_coords_missing() -> None:
    seen: dict[str, str] = {}

    def fake_geocoder(query: str) -> GeocodedAddress:
        seen["query"] = query
        return GeocodedAddress(33.5, 126.5, "제주 어딘가")

    coord, geocoded = resolve_coord(
        _item(latitude=None, longitude=None, address="제주시 어딘가"), fake_geocoder
    )

    assert geocoded is True
    assert coord == (33.5, 126.5)
    assert seen["query"] == "제주시 어딘가"


def test_existing_coords_skip_geocoding() -> None:
    coord, geocoded = resolve_coord(
        _item(), lambda _query: pytest.fail("좌표가 있으면 지오코딩하면 안 된다")
    )
    assert geocoded is False
    assert coord == (33.4241, 126.9296)


# --- 기존 행 정책 갱신(--update-existing) ------------------------------------


def test_policy_column_values_maps_and_forces_internal() -> None:
    values = policy_column_values(
        {
            "policy_type": "partial_allowed",
            "leash_required": True,
            "allowed_sizes": ["small"],
            "max_weight_kg": 13,
            "caution_note": "소형견",
            "source_url": "https://x",
            "verified_at": "2026-09-08",
        }
    )
    assert values["policy_type"] == PetPolicyType.PARTIAL_ALLOWED
    assert values["source"] == DataProvider.INTERNAL
    assert values["reliability_score"] == Decimal(90)
    assert values["leash_required"] is True
    assert values["allowed_sizes"] == ["small"]
    assert values["max_weight_kg"] == Decimal("13")
    assert values["verified_at"].isoformat().startswith("2026-09-08")
    # 주어지지 않은 선택 컬럼은 넣지 않는다(덮어쓰지 않음).
    assert "carrier_required" not in values


def test_validate_updates_rejects_missing_source_url() -> None:
    update = {"name": "천지연폭포", "pet_policy": {"policy_type": "outdoor_only"}}
    errors = validate_updates([update])
    assert any("source_url" in error.reason for error in errors)
