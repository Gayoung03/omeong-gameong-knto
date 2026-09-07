"""여행 속도별 일정 조립 정책.

문서에 합의한 dict 모양을 유지해 3단계에서 변환 없이 쓴다. 반려동물 특성에 따른
하루 구성 조정은 effective_rule 이 이 표를 복사해 반영한다(route-redesign §3.3).
"""

from collections.abc import Sequence
from typing import TypedDict

from app.db.models.enums import PetActivityLevel, PetEnergyLevel, TripPace
from app.recommend.schemas import PetProfile


class PaceRule(TypedDict):
    places_per_day: int
    rest_min: int
    window: tuple[str, str]
    # 반려동물 차멀미 시 구간 이동시간 상한(분). None 이면 상한 없음.
    max_travel_min: int | None


PACE: dict[str, PaceRule] = {
    # 장소 수만 줄이면 오후 일찍 일정이 끝난다. 방문 사이 여백도 넓혀
    # 하루 전체를 천천히 쓰는 프리셋으로 만든다.
    "relaxed": {
        "places_per_day": 3, "rest_min": 110, "window": ("10:00", "19:00"), "max_travel_min": None
    },
    "normal": {
        "places_per_day": 4, "rest_min": 25, "window": ("09:00", "19:00"), "max_travel_min": None
    },
    "packed": {
        "places_per_day": 5, "rest_min": 15, "window": ("08:00", "21:00"), "max_travel_min": None
    },
}

#: 하루 구성을 낮추는 나이 기준(만 나이).
SENIOR_AGE_YEARS = 8
#: 차멀미 반려동물이 있을 때의 구간 이동시간 상한(분).
CAR_SICKNESS_MAX_TRAVEL_MIN = 40


def _is_slow_pet(pet: PetProfile) -> bool:
    """이 반려동물 때문에 하루를 늦춰야 하는가.

    나이는 노령이면 감속. 활동량은 **이번 여행 컨디션(energy_level)이 평소
    활동량(activity_level)을 덮어쓴다**(계약 §3.4: energy_level > activity_level >
    미적용). 그래서 평소 저활동이어도 이번에 컨디션이 좋으면 감속하지 않는다.
    """
    if pet.age_years is not None and pet.age_years >= SENIOR_AGE_YEARS:
        return True
    effective_level = pet.energy_level or pet.activity_level
    return effective_level in (PetEnergyLevel.LOW, PetActivityLevel.LOW)


def effective_rule(pace: TripPace, pets: Sequence[PetProfile]) -> PaceRule:
    """반려동물 나이·활동량·이번 컨디션·차멀미를 반영한 하루 구성 규칙.

    - 노령(만 8세 이상)이거나 유효 활동량(energy_level or activity_level)이 low 인
      반려동물이 하나라도 있으면 하루 장소 수 −1(최소 2)·휴식 +15.
    - car_sickness 인 반려동물이 하나라도 있으면 구간 이동시간 상한 40분·휴식 +10.
    - 저하 조건이 없으면 변경 없음. 반려동물이 없으면 PACE 표 그대로.
    """
    rule: PaceRule = dict(PACE[pace.value])  # type: ignore[assignment]
    if not pets:
        return rule

    if any(_is_slow_pet(pet) for pet in pets):
        rule["places_per_day"] = max(2, rule["places_per_day"] - 1)
        rule["rest_min"] += 15
    if any(pet.car_sickness for pet in pets):
        rule["max_travel_min"] = CAR_SICKNESS_MAX_TRAVEL_MIN
        rule["rest_min"] += 10
    return rule
