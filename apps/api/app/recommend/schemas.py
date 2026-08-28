"""1·2단계 추천과 3단계 동선 조립 사이의 계약.

이 모듈의 필드를 바꾸는 것은 팀원의 itinerary fixture에도 영향을
준다. 임의의 dict 대신 Pydantic 모델을 경계에서 사용한다.
"""

import uuid
from datetime import time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models.enums import PetPolicyType, PlaceEnvironment, ScheduleItemType


class RecommendationSchema(BaseModel):
    """추천 엔진 내부 계약은 snake_case로 고정하고 추가 필드를 막는다."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class BusinessHour(RecommendationSchema):
    """일정 조립이 방문 시각을 검증할 수 있는 하루의 영업시간."""

    day_of_week: int = Field(ge=0, le=6, description="0=일요일, 6=토요일")
    opens_at: time | None = None
    closes_at: time | None = None
    break_start_at: time | None = None
    break_end_at: time | None = None
    is_closed: bool = False

    @model_validator(mode="after")
    def validate_time_pairs(self) -> "BusinessHour":
        for start_name, end_name in (
            ("opens_at", "closes_at"),
            ("break_start_at", "break_end_at"),
        ):
            start = getattr(self, start_name)
            end = getattr(self, end_name)
            if (start is None) != (end is None):
                raise ValueError(f"{start_name}과 {end_name}은 함께 설정해야 합니다")
        return self


class PetPolicy(RecommendationSchema):
    """하드 필터와 반려 편의 점수에 필요한 정책 스냅샷."""

    policy_type: PetPolicyType
    allowed_species: list[str] = Field(default_factory=list)
    allowed_sizes: list[str] = Field(default_factory=list)
    max_weight_kg: float | None = Field(default=None, ge=0)
    carrier_required: bool | None = None
    leash_required: bool | None = None
    vaccination_required: bool | None = None
    reliability_score: float | None = Field(default=None, ge=0, le=100)


class Candidate(RecommendationSchema):
    """1단계 하드 필터를 통과한 장소."""

    place_id: uuid.UUID
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    item_type: ScheduleItemType
    environment: PlaceEnvironment | None
    average_stay_minutes: int = Field(gt=0)
    tags: list[str] = Field(default_factory=list)
    amenities: list[str] = Field(default_factory=list)
    rating_avg: float | None = Field(default=None, ge=1, le=5)
    saved_count: int = Field(default=0, ge=0)
    pet_policy: PetPolicy | None = None
    business_hours: list[BusinessHour] = Field(default_factory=list)


class Weights(RecommendationSchema):
    """2단계 점수 합성에 쓰는 6개 가중치(합계 1)."""

    preference: float = Field(ge=0, le=1)
    pet: float = Field(ge=0, le=1)
    proximity: float = Field(ge=0, le=1)
    rating: float = Field(ge=0, le=1)
    weather: float = Field(ge=0, le=1)
    popularity: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_sum(self) -> "Weights":
        if abs(sum(self.model_dump().values()) - 1.0) > 1e-9:
            raise ValueError("가중치 합은 1이어야 합니다")
        return self


class ScoredCandidate(Candidate):
    """2단계의 최종 출력이자 3단계의 입력."""

    total_score: float = Field(ge=0, le=1)
    sub_scores: dict[str, float]
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sub_scores(self) -> "ScoredCandidate":
        expected = set(Weights.model_fields)
        if set(self.sub_scores) != expected:
            raise ValueError(f"sub_scores 키는 {sorted(expected)}와 일치해야 합니다")
        if any(score < 0 or score > 1 for score in self.sub_scores.values()):
            raise ValueError("sub_scores 값은 0~1이어야 합니다")
        return self
