"""request_text 구조화 추출 (routes.md·ai-io-column-design 8.3-3).

파싱·병합은 순수 함수로, generate_route 연동은 추출 함수 모킹으로 본다 —
실제 OpenAI 호출 없이 "실패해도 생성이 계속 간다"가 핵심 계약이다.
"""

import json

import pytest

from app.integrations.llm import request_intent as ri
from app.integrations.llm.request_intent import (
    RequestIntent,
    extract_request_intent,
    merge_preferred_tags,
    parse_intent_arguments,
)

# ---------------------------------------------------------------------------
# parse_intent_arguments — 어휘 이중 방어
# ---------------------------------------------------------------------------


def test_표준_태그만_남긴다() -> None:
    raw = json.dumps({"preferred_tags": ["바다", "카페", "개인서사같은값", "산책"]})
    assert parse_intent_arguments(raw).preferred_tags == ("바다", "카페", "산책")


def test_중복은_한_번만() -> None:
    raw = json.dumps({"preferred_tags": ["바다", "바다", "휴식"]})
    assert parse_intent_arguments(raw).preferred_tags == ("바다", "휴식")


def test_빈_결과도_유효하다() -> None:
    assert parse_intent_arguments(json.dumps({"preferred_tags": []})).preferred_tags == ()
    assert parse_intent_arguments(json.dumps({})).preferred_tags == ()


# ---------------------------------------------------------------------------
# merge_preferred_tags — 기존 우선 합집합
# ---------------------------------------------------------------------------


def test_기존_태그는_절대_사라지지_않는다() -> None:
    merged = merge_preferred_tags(["바다", "category:restaurant"], ("산책",))
    assert merged == {"바다", "category:restaurant", "산책"}


def test_기존이_없으면_추출값만() -> None:
    assert merge_preferred_tags(None, ("휴식",)) == {"휴식"}
    assert merge_preferred_tags([], ()) == frozenset()


# ---------------------------------------------------------------------------
# extract_request_intent — 실패는 조용히 None
# ---------------------------------------------------------------------------


def test_빈_문장이나_키_없음은_None(monkeypatch: pytest.MonkeyPatch) -> None:
    assert extract_request_intent("   ") is None
    monkeypatch.setattr(ri.settings, "openai_api_key", "")
    assert extract_request_intent("산책하기 좋은 곳") is None


def test_호출_실패는_None(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ri.settings, "openai_api_key", "test-key")

    class Boom:
        def __init__(self, **kwargs):
            raise RuntimeError("네트워크 불가")

    monkeypatch.setattr(ri, "OpenAI", Boom)
    assert extract_request_intent("산책하기 좋은 곳") is None


# ---------------------------------------------------------------------------
# generate_route 병합 — 실패 무시·요청 행 불변 (실제 생성 경로 통합)
# ---------------------------------------------------------------------------


def _generate_with_request_text(client, db, place, monkeypatch, *, intent_behavior):
    """test_route_requests 의 생성 픽스처를 재사용해 requestText 포함 요청을 돌린다."""
    import uuid as uuid_module

    from fastapi.testclient import TestClient  # noqa: F401 — 시그니처 문서화용

    from app.api.v1.endpoints import routes
    from app.db.models import Place, Route, RouteRequest
    from app.recommend.tmap import RouteLeg
    from app.services import route_recommendation as rr

    monkeypatch.setattr(rr, "_tour_api_places", lambda *_args: [])
    monkeypatch.setattr(routes, "get_nearby_places", lambda *_a, **_k: [])
    monkeypatch.setattr(routes, "run_route_generation", lambda _route_id, _open: None)
    monkeypatch.setattr(
        rr, "get_route",
        lambda *_a, **_k: RouteLeg(distance_m=0, duration_min=0, polyline=None),
    )
    monkeypatch.setattr(rr, "get_precipitation_probabilities", lambda *_a, **_k: {})
    monkeypatch.setattr(rr, "extract_request_intent", intent_behavior)

    restaurant = Place(
        id=uuid_module.uuid4(),
        name="동반 가능 저녁 식당",
        category="restaurant",
        latitude=33.395,
        longitude=126.240,
        average_stay_minutes=60,
    )
    db.add(restaurant)
    db.flush()

    payload = {
        "title": "몽이랑 제주",
        "startAt": "2026-09-10T09:00:00+09:00",
        "endAt": "2026-09-10T18:00:00+09:00",
        "departurePlaceId": str(place.id),
        "pace": "relaxed",
        "transport": "rental_car",
        "preferredTags": ["바다"],
        "priorityPreset": "pet",
        "userCriteria": [],
        "requestText": "우리 애랑 산책할 곳 위주로 부탁해요",
    }
    created = client.post("/api/v1/route-requests", json=payload).json()
    route_id = uuid_module.UUID(created["routeId"])

    rr.generate_route(db, route_id)
    db.expire_all()
    route = db.get(Route, route_id)
    request = db.get(RouteRequest, route.route_request_id)
    return route, request


def test_추출이_실패해도_추천_생성은_진행된다(client, db, place, monkeypatch) -> None:
    calls = {"n": 0}

    def explode(text: str):
        calls["n"] += 1
        raise RuntimeError("LLM 죽음")

    route, request = _generate_with_request_text(
        client, db, place, monkeypatch, intent_behavior=explode
    )

    assert calls["n"] == 1  # 추출을 시도는 했고
    assert route.status.value == "generated"  # 생성은 그래도 끝났다


def test_추출_태그는_이번_생성에만_쓰고_요청_행은_바꾸지_않는다(
    client, db, place, monkeypatch
) -> None:
    route, request = _generate_with_request_text(
        client, db, place, monkeypatch,
        intent_behavior=lambda text: RequestIntent(preferred_tags=("산책",)),
    )

    assert route.status.value == "generated"
    # 요청 행의 preferred_tags 는 사용자가 보낸 그대로 — 추출값이 영속화되면 안 된다.
    assert request.preferred_tags == ["바다"]
    assert request.request_text == "우리 애랑 산책할 곳 위주로 부탁해요"