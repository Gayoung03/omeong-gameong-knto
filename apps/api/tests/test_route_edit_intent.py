"""루트 수정 LLM의 구조화 결과 검증."""

import json
import uuid

import pytest

from app.db.models.enums import ScheduleItemType
from app.integrations.llm.route_edit import RouteEditError, _parse_arguments


def test_parse_route_edit_intent_accepts_only_current_item() -> None:
    item_id = uuid.uuid4()
    intent = _parse_arguments(
        json.dumps(
            {
                "target_item_id": str(item_id),
                "requested_category": "cafe",
                "preferred_tags": ["카페", "휴식", "카페"],
                "location_anchor": "stay",
                "interpretation": "첫 카페를 조용한 카페로 교체",
            }
        ),
        {item_id},
    )

    assert intent.target_item_id == item_id
    assert intent.requested_category == ScheduleItemType.CAFE
    assert intent.preferred_tags == ("카페", "휴식")
    assert intent.location_anchor == "stay"


def test_parse_route_edit_intent_rejects_hallucinated_item() -> None:
    with pytest.raises(RouteEditError, match="현재 일정에 없는"):
        _parse_arguments(
            json.dumps(
                {
                    "target_item_id": str(uuid.uuid4()),
                    "requested_category": None,
                    "preferred_tags": [],
                    "location_anchor": "current",
                    "interpretation": "다른 장소로 교체",
                }
            ),
            {uuid.uuid4()},
        )


def test_parse_route_edit_intent_rejects_unknown_tag() -> None:
    item_id = uuid.uuid4()
    with pytest.raises(RouteEditError, match="지원하지 않는 선호 태그"):
        _parse_arguments(
            json.dumps(
                {
                    "target_item_id": str(item_id),
                    "requested_category": None,
                    "preferred_tags": ["모델이 만든 태그"],
                    "location_anchor": "current",
                    "interpretation": "교체",
                }
            ),
            {item_id},
        )
