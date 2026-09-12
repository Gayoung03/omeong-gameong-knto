"""장소 검색 조건 검사기(`check_place_search`)와 무게 인자 검사기 검증.

**실제 호출을 하지 않는다.** 가짜 도구 호출 기록과, 2026-09-12 팀 RDS 실행에서
실제로 남은 인자(`tmp/chat-quality-places.md`)를 그대로 옮겨 와 돌린다 — 검사기를
고칠 때마다 요금을 내고 다시 물어볼 수는 없다.
"""

import json

import pytest

from scripts.chat_quality_check import PLACE_QUESTIONS
from scripts.measure_chat_llm import (
    SEARCH_MISSING,
    SEARCH_NONE,
    SEARCH_OK,
    SEARCH_SKIP,
    SEARCH_WRONG,
    _pet_weight_in_question,
    _weight_arg_status,
    check_place_search,
)


def _place_call(**arguments) -> dict:
    """`_trace_dispatch` 가 남기는 모양 그대로의 가짜 `search_places` 호출."""
    return {
        "tool": "search_places",
        "args": json.dumps(arguments, ensure_ascii=False),
        "hits": 0,
        "result": "[]",
    }


def _spec(question_id: int) -> dict:
    return next(q for q in PLACE_QUESTIONS if q["id"] == question_id)


def _expected(question_id: int) -> dict:
    return _spec(question_id)["expected_search"]


# --- 기대 조건 자체가 어휘와 어긋나지 않는지 -------------------------------------


def test_expected_values_exist_in_vocabulary() -> None:
    """기대값이 실제 어휘에 없는 값이면 영영 통과할 수 없는 검사가 된다."""
    from app.rag.vocabulary import CATEGORIES, REGIONS, TAGS

    allowed_by_dimension = {"region": REGIONS, "category": CATEGORIES, "tags": TAGS}
    for question in PLACE_QUESTIONS:
        for dimension, rule in question["expected_search"].items():
            if not isinstance(rule, dict):
                continue  # 보류
            for value in rule["allowed"]:
                assert value in allowed_by_dimension[dimension], (
                    f"{question['id']}번 {dimension} 기대값 {value!r} 이 어휘에 없다"
                )


def test_every_place_question_has_expectation_or_reason() -> None:
    """보류는 괜찮지만 **이유 없이 빠뜨린 것**은 안 된다."""
    for question in PLACE_QUESTIONS:
        expected_search = question["expected_search"]
        assert expected_search, f"{question['id']}번에 expected_search 가 없다"
        for dimension, rule in expected_search.items():
            if isinstance(rule, dict):
                assert rule["why"].strip(), f"{question['id']}번 {dimension} 에 근거가 없다"
            else:
                assert rule.startswith("보류"), (
                    f"{question['id']}번 {dimension} 은 dict 가 아니면 '보류'로 시작해야 한다"
                )


# --- 네 가지 경우를 구분하는지 ---------------------------------------------------


def test_correct_search_passes() -> None:
    got = check_place_search(_expected(1), [_place_call(region="서귀포시/모슬포", category="cafe")])
    assert got["verdict"] == SEARCH_OK


def test_no_search_is_its_own_verdict() -> None:
    got = check_place_search(_expected(1), [])
    assert got["verdict"] == SEARCH_NONE


def test_other_tools_do_not_count_as_place_search() -> None:
    """가이드만 찾고 장소는 안 찾았으면 '검색안함' 이다."""
    trace = [{"tool": "search_guides", "args": "{}", "hits": 0, "result": "[]"}]
    assert check_place_search(_expected(1), trace)["verdict"] == SEARCH_NONE


def test_missing_category_is_distinguished_from_wrong_value() -> None:
    got = check_place_search(_expected(1), [_place_call(region="서귀포시/모슬포")])
    assert got["verdict"] == SEARCH_MISSING
    assert "category" in got["reason"]


def test_wrong_region_is_flagged() -> None:
    got = check_place_search(_expected(1), [_place_call(region="애월/한림/협재", category="cafe")])
    assert got["verdict"] == SEARCH_WRONG
    assert "애월/한림/협재" in got["reason"]


def test_invented_region_outside_vocabulary_is_flagged() -> None:
    """어휘 밖 값은 DB 에 없어 검색이 조용히 0건이 된다."""
    got = check_place_search(_expected(6), [_place_call(region="제주 동쪽", category="cafe")])
    assert got["verdict"] == SEARCH_WRONG


# --- 맞는 호출이 틀린 호출을 가리지 않는지 -----------------------------------------


def test_one_correct_call_does_not_hide_a_wrong_one() -> None:
    got = check_place_search(
        _expected(3),
        [
            _place_call(region="제주시/제주국제공항", category="cafe"),
            _place_call(region="서귀포시/모슬포", category="cafe"),
        ],
    )
    assert got["verdict"] == SEARCH_WRONG
    assert "2번째 호출" in got["reason"]
    assert len(got["calls"]) == 2


def test_splitting_by_allowed_regions_is_not_a_failure() -> None:
    """권역을 나눠 검색하는 것은 프롬프트가 시키는 일이다."""
    got = check_place_search(
        _expected(1),
        [
            _place_call(region="서귀포시/모슬포", category="cafe"),
            _place_call(region="중문", category="cafe"),
        ],
    )
    assert got["verdict"] == SEARCH_OK


def test_broadening_after_a_correct_call_is_not_missing() -> None:
    """조건을 풀어 다시 찾는 것(B7)은 실패가 아니다 — 앞에서 제대로 찾았다."""
    got = check_place_search(
        _expected(1),
        [
            _place_call(region="서귀포시/모슬포", category="cafe"),
            _place_call(region="서귀포시/모슬포"),
        ],
    )
    assert got["verdict"] == SEARCH_OK


def test_region_omitted_everywhere_is_missing() -> None:
    got = check_place_search(_expected(1), [_place_call(category="cafe")])
    assert got["verdict"] == SEARCH_MISSING
    assert "region" in got["reason"]


# --- 보류 -----------------------------------------------------------------------


def test_region_is_optional_for_whole_island_question() -> None:
    """'제주도' 질문은 권역을 생략해도 답이 된다."""
    got = check_place_search(_expected(6), [_place_call(category="cafe")])
    assert got["verdict"] == SEARCH_OK


def test_ambiguous_dimensions_are_not_judged() -> None:
    """5번은 종류가 보류라, 지역만 맞으면 통과한다."""
    got = check_place_search(_expected(5), [_place_call(region="중문")])
    assert got["verdict"] == SEARCH_OK


def test_all_skip_expectation_returns_skip() -> None:
    got = check_place_search({"category": "보류 — 이유"}, [_place_call(category="cafe")])
    assert got["verdict"] == SEARCH_SKIP


def test_questions_without_expectation_are_skipped() -> None:
    """규정 문항처럼 `expected_search` 가 없는 문항은 판단하지 않는다."""
    assert check_place_search(None, [])["verdict"] == SEARCH_SKIP


# --- 실제로 저장된 기록(2026-09-12 팀 RDS 실행)으로 -------------------------------

#: `tmp/chat-quality-places.md` 에 남은 gpt-4o-mini 의 실제 호출 인자다.
#: 추가 과금 없이 검사기를 검증하려고 그대로 옮겨 왔다.
RECORDED_RUN = {
    1: {"region": "서귀포시/모슬포", "category": "cafe"},
    2: {"region": "서귀포시/모슬포", "pet_policy": ["indoor_allowed", "unknown"]},
    3: {"region": "제주시/제주국제공항", "category": "cafe"},
    4: {"region": "애월/한림/협재", "category": "cafe", "pet_policy": ["unknown"]},
    5: {"region": "중문"},
    6: {"category": "cafe", "pet_policy": ["unknown"], "limit": 3},
}


@pytest.mark.parametrize("question_id", sorted(RECORDED_RUN))
def test_recorded_run_is_judged_correct(question_id: int) -> None:
    """그날 기록은 여섯 문항 모두 지역·종류를 제대로 집었다.

    2번은 종류·태그가 보류라 지역만 보고, 5번은 종류가 보류, 6번은 지역이
    선택이다. 하나라도 실패로 잡히면 기대 조건이 너무 좁게 잡힌 것이다.
    """
    got = check_place_search(_expected(question_id), [_place_call(**RECORDED_RUN[question_id])])
    assert got["verdict"] == SEARCH_OK, got["reason"]


# --- 무게 인자 -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("강아지가 12kg인데 비행기로 제주도 데려갈 수 있을까요?", 12.0),
        ("20kg 대형견인데 배로 제주도 갈 수 있나요?", 20.0),
        ("우리 고양이 4.5kg이요", 4.5),
        # 아래는 전부 판단 보류 — 숫자가 반려동물 무게가 아니거나 대상이 갈린다.
        ("항공사 기내 제한이 7kg인가요?", None),
        ("강아지 6kg, 케이지 2kg인데 가능할까요?", None),
        ("케이지 포함 9kg 넘으면 안 되나요?", None),
        ("반려동물 데리고 탈 수 있는 제주행 배편 알려주세요.", None),
    ],
)
def test_pet_weight_is_read_only_when_unambiguous(question: str, expected) -> None:
    assert _pet_weight_in_question(question) == expected


def _rule_call(**arguments) -> dict:
    return {
        "tool": "search_transport_rules",
        "args": json.dumps(arguments, ensure_ascii=False),
        "hits": 0,
        "result": "[]",
    }


def test_weight_arg_value_is_checked_not_just_presence() -> None:
    question = "강아지가 12kg인데 비행기로 제주도 데려갈 수 있을까요?"
    assert _weight_arg_status(question, [_rule_call(pet_weight_kg=12)]) == "정확"
    assert _weight_arg_status(question, [_rule_call(pet_weight_kg=9)]) == "값틀림"
    assert _weight_arg_status(question, [_rule_call(carrier_type="airline")]) == "누락"


def test_weight_arg_is_skipped_when_target_is_unclear() -> None:
    assert _weight_arg_status("항공사 기내 제한이 7kg인가요?", [_rule_call()]) is None
