"""자연어 루트 수정 요청을 제한된 교체 조건으로 해석한다.

일반 챗봇과 별도 모듈이다. 이 LLM은 장소를 추천하거나 DB를 조회하지 않고,
사용자 문장에서 교체 대상과 원하는 조건만 구조화한다.
"""

import json
import uuid
from dataclasses import dataclass

from openai import APITimeoutError, OpenAI

from app.core.config import settings
from app.db.models.enums import ScheduleItemType
from app.recommend.config.tags import STANDARD_TAGS

EDITABLE_CATEGORIES = tuple(
    item.value for item in ScheduleItemType if item != ScheduleItemType.CUSTOM
)


class RouteEditError(RuntimeError):
    """루트 수정 의도를 해석하지 못했다."""


class RouteEditTimeoutError(RouteEditError):
    """루트 수정 의도 해석이 제한 시간을 넘겼다."""


@dataclass(frozen=True)
class RouteItemContext:
    item_id: uuid.UUID
    name: str
    category: str


@dataclass(frozen=True)
class RouteEditIntent:
    target_item_id: uuid.UUID
    requested_category: ScheduleItemType | None
    preferred_tags: tuple[str, ...]
    location_anchor: str
    interpretation: str


def interpret_route_edit(items: list[RouteItemContext], instruction: str) -> RouteEditIntent:
    """현재 일정 항목 안에서 교체 대상과 새 조건만 선택하게 한다."""

    if not items:
        raise RouteEditError("수정할 일정 항목이 없습니다")
    if not settings.openai_api_key:
        raise RouteEditError("OPENAI_API_KEY가 설정되지 않았습니다")

    tool = _edit_tool(items)
    current_items = [
        {"itemId": str(item.item_id), "name": item.name, "category": item.category}
        for item in items
    ]
    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.route_edit_timeout_seconds,
        max_retries=0,
    )
    try:
        completion = client.chat.completions.create(
            model=settings.route_edit_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 여행 일정 수정 의도 해석기다. 현재 일정에 있는 항목 하나만 "
                        "교체 대상으로 고르고 사용자가 원하는 카테고리와 태그를 구조화한다. "
                        "숙소나 호텔에서 가까운 곳을 원하면 location_anchor를 stay로 둔다. "
                        "새 장소를 직접 만들거나 추천하지 않는다."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"currentItems": current_items, "instruction": instruction},
                        ensure_ascii=False,
                    ),
                },
            ],
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": "interpret_route_edit"}},
        )
    except APITimeoutError as error:
        raise RouteEditTimeoutError("루트 수정 해석이 시간을 초과했습니다") from error
    except Exception as error:
        raise RouteEditError("루트 수정 요청을 해석하지 못했습니다") from error

    calls = completion.choices[0].message.tool_calls
    if not calls:
        raise RouteEditError("루트 수정 조건을 받지 못했습니다")
    return _parse_arguments(calls[0].function.arguments, {item.item_id for item in items})


def _edit_tool(items: list[RouteItemContext]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": "interpret_route_edit",
            "description": "교체할 일정 항목과 사용자가 원하는 대체 조건을 추출한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_item_id": {
                        "type": "string",
                        "enum": [str(item.item_id) for item in items],
                    },
                    "requested_category": {
                        "type": ["string", "null"],
                        "enum": [*EDITABLE_CATEGORIES, None],
                    },
                    "preferred_tags": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(STANDARD_TAGS)},
                    },
                    "location_anchor": {
                        "type": "string",
                        "enum": ["current", "stay"],
                        "description": "숙소 근처 요청이면 stay, 그 외에는 current",
                    },
                    "interpretation": {"type": "string"},
                },
                "required": [
                    "target_item_id",
                    "requested_category",
                    "preferred_tags",
                    "location_anchor",
                    "interpretation",
                ],
                "additionalProperties": False,
            },
        },
    }


def _parse_arguments(raw: str, allowed_item_ids: set[uuid.UUID]) -> RouteEditIntent:
    try:
        arguments = json.loads(raw)
        target_item_id = uuid.UUID(arguments["target_item_id"])
        category = arguments.get("requested_category")
        preferred_tags = tuple(dict.fromkeys(arguments.get("preferred_tags") or []))
        location_anchor = str(arguments["location_anchor"])
        interpretation = str(arguments["interpretation"]).strip()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RouteEditError("루트 수정 조건 형식이 올바르지 않습니다") from error

    if target_item_id not in allowed_item_ids:
        raise RouteEditError("현재 일정에 없는 항목을 수정할 수 없습니다")
    if not set(preferred_tags).issubset(STANDARD_TAGS):
        raise RouteEditError("지원하지 않는 선호 태그가 포함되어 있습니다")
    if location_anchor not in {"current", "stay"}:
        raise RouteEditError("지원하지 않는 거리 기준입니다")
    try:
        requested_category = ScheduleItemType(category) if category else None
    except ValueError as error:
        raise RouteEditError("지원하지 않는 장소 유형입니다") from error
    if requested_category == ScheduleItemType.CUSTOM:
        raise RouteEditError("직접 입력 일정은 추천 장소 유형으로 사용할 수 없습니다")
    if not interpretation:
        raise RouteEditError("수정 요청 설명이 비어 있습니다")

    return RouteEditIntent(
        target_item_id=target_item_id,
        requested_category=requested_category,
        preferred_tags=preferred_tags,
        location_anchor=location_anchor,
        interpretation=interpretation,
    )
