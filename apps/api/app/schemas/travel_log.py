"""여행기록 API 스키마.

`visitedAt` 은 **시각**이다 — 리뷰의 `visitedAt` 은 날짜라 같은 이름이지만
형식이 다르다(docs/api/travel-logs.md).

`routeId` 는 DB 의 `travel_logs.route_id` 다. 앱 화면 파라미터 이름이 `tripId`
라서 헷갈리기 쉬운데, **API 는 `routeId` 로 통일**한다.
"""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.db.models.enums import GenerationStatus, MomentMood, WritingStyle
from app.schemas.base import APISchema


class TravelLogCompanion(APISchema):
    """함께한 반려동물의 스냅샷.

    `petId` 는 `ON DELETE SET NULL` 이라 프로필을 완전히 지우면 None 이 된다.
    그래도 이름·사진은 남아서 화면이 깨지지 않는다.
    """

    pet_id: uuid.UUID | None
    name_snapshot: str
    profile_image_snapshot: str | None


class TravelLogItem(APISchema):
    """기록 한 건.

    목록·상세·그룹의 `previewLogs` 가 **모두 이 스키마 하나**를 쓴다.
    셋을 따로 두면 필드가 하나 늘 때마다 세 곳을 고쳐야 한다.
    """

    id: uuid.UUID
    route_id: uuid.UUID | None
    place_id: uuid.UUID | None
    place_name_snapshot: str
    recorded_date: date
    visited_at: datetime | None
    original_image_url: str
    generated_image_url: str | None
    writing_style: WritingStyle
    mood: MomentMood | None
    generation_status: GenerationStatus
    personal_message: str | None
    is_representative: bool
    companions: list[TravelLogCompanion]
    created_at: datetime


class TravelLogListResponse(APISchema):
    items: list[TravelLogItem]
    total: int
    limit: int
    offset: int


class TravelLogUpdate(APISchema):
    """보낸 필드만 수정한다.

    `originalImageUrl` 과 `writingStyle` 은 **여기 없다.** 다시 만들려면
    재생성(`POST /travel-logs/{logId}/regenerate`)을 쓴다.

    `petIds` 를 보내면 기존 `travel_log_pets` 를 전부 지우고 새로 저장한다.
    이때 이름·사진 스냅샷도 **현재 시점 값**으로 갱신된다.
    """

    personal_message: str | None = None
    recorded_date: date | None = None
    visited_at: datetime | None = None
    place_id: uuid.UUID | None = None
    place_name: str | None = None
    mood: MomentMood | None = None
    is_representative: bool | None = None
    pet_ids: list[uuid.UUID] | None = None


# ---------------------------------------------------------------------------
# GET /travel-logs/groups
# ---------------------------------------------------------------------------
# 앱 목록 화면은 기록을 여행 단위 / 월 단위로 묶어 보여준다. 앱이 매번 직접
# 묶지 않도록 서버가 그룹을 만들어 내려준다.


class TravelLogRouteSummary(APISchema):
    """여행 단위 그룹의 머리말.

    `companions` 는 **여행 자체의 반려동물**이라 기록의 `companions`
    (`travel_log_pets`)와 출처가 다르다. 어느 한쪽만 고치지 않는다.
    """

    id: uuid.UUID
    title: str
    start_date: date | None
    end_date: date | None
    place_name_snapshot: str | None
    companions: list[TravelLogCompanion]
    log_count: int
    preview_logs: list[TravelLogItem]


class TravelLogMonthSummary(APISchema):
    """여행에 속하지 않은 개별 기록을 연·월로 묶은 것."""

    year: int
    month: int
    log_count: int
    preview_logs: list[TravelLogItem]


class TravelLogRouteGroup(APISchema):
    kind: Literal["route"] = "route"
    route: TravelLogRouteSummary


class TravelLogMonthGroup(APISchema):
    kind: Literal["ungrouped"] = "ungrouped"
    group: TravelLogMonthSummary


class TravelLogGroupsResponse(APISchema):
    items: list[TravelLogRouteGroup | TravelLogMonthGroup] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
