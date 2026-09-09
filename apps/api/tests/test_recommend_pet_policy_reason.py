"""`recommendationReason` 규칙 템플릿 단위 테스트 (순수 함수)."""

from datetime import UTC, datetime

import pytest

from app.db.models.enums import DataProvider, PetPolicyType
from app.recommend.config.pet_policy_reason import NEEDS_CHECK_REASON, reason_for
from app.recommend.schemas import CandidateTier, PetPolicy


def _policy(**overrides: object) -> PetPolicy:
    values: dict[str, object] = {"policy_type": PetPolicyType.OUTDOOR_ONLY}
    values.update(overrides)
    return PetPolicy(**values)


def test_verified_outdoor_with_leash_and_source_matches_spec_example() -> None:
    policy = _policy(
        policy_type=PetPolicyType.OUTDOOR_ONLY,
        leash_required=True,
        source=DataProvider.TOUR_API,
        verified_at=datetime(2026, 7, 20, 1, 0, tzinfo=UTC),  # 10:00 KST
    )

    reason = reason_for(policy, CandidateTier.VERIFIED)

    expected = (
        "목줄 착용 시 야외 동반 가능 · 한국관광공사 반려동물 동반 정보 기준 (2026-07-20 확인)"
    )
    assert reason == expected


def test_leash_and_muzzle_share_verb_joined_with_middle_dot() -> None:
    policy = _policy(leash_required=True, muzzle_required=True, source=DataProvider.INTERNAL)

    reason = reason_for(policy, CandidateTier.VERIFIED)

    assert reason.startswith("목줄·입마개 착용 시 야외 동반 가능")


def test_leash_and_carrier_different_verbs_joined_with_comma() -> None:
    policy = _policy(leash_required=True, carrier_required=True, source=DataProvider.INTERNAL)

    reason = reason_for(policy, CandidateTier.VERIFIED)

    assert reason.startswith("목줄 착용, 케이지 이용 시 야외 동반 가능")


def test_all_three_conditions_group_by_verb() -> None:
    policy = _policy(
        leash_required=True,
        muzzle_required=True,
        carrier_required=True,
        source=DataProvider.INTERNAL,
    )

    reason = reason_for(policy, CandidateTier.VERIFIED)

    assert reason.startswith("목줄·입마개 착용, 케이지 이용 시 야외 동반 가능")


def test_no_conditions_omits_prefix() -> None:
    policy = _policy(policy_type=PetPolicyType.INDOOR_ALLOWED, source=DataProvider.KAKAO)

    reason = reason_for(policy, CandidateTier.VERIFIED)

    assert reason == "실내외 동반 가능 · 카카오 로컬 정보 기준"


def test_missing_verified_at_omits_parenthesis() -> None:
    policy = _policy(source=DataProvider.VISITJEJU)

    reason = reason_for(policy, CandidateTier.VERIFIED)

    assert reason == "야외 동반 가능 · 비짓제주 정보 기준"


def test_caution_note_appended_last() -> None:
    policy = _policy(source=DataProvider.INTERNAL, caution_note="대형견은 입마개를 착용해 주세요.")

    reason = reason_for(policy, CandidateTier.VERIFIED)

    assert reason.endswith("· 대형견은 입마개를 착용해 주세요.")


def test_source_without_policy_label_uses_fallback() -> None:
    policy = _policy(source=DataProvider.TMAP)

    reason = reason_for(policy, CandidateTier.VERIFIED)

    assert "제공 정보 기준" in reason


@pytest.mark.parametrize("tier", [CandidateTier.NEEDS_CHECK, CandidateTier.BLOCKED])
def test_non_verified_tier_returns_needs_check_message(tier: CandidateTier) -> None:
    policy = _policy(leash_required=True, source=DataProvider.TOUR_API)

    assert reason_for(policy, tier) == NEEDS_CHECK_REASON


def test_none_policy_returns_needs_check_message() -> None:
    assert reason_for(None, CandidateTier.VERIFIED) == NEEDS_CHECK_REASON


def test_partial_allowed_sentence() -> None:
    policy = _policy(policy_type=PetPolicyType.PARTIAL_ALLOWED, source=DataProvider.KCISA)

    reason = reason_for(policy, CandidateTier.VERIFIED)

    assert reason == "일부 구역 동반 가능 · 한국문화정보원 반려동물 동반 정보 기준"
