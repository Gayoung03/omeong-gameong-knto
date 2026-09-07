"""카테고리별 기본 체류시간(분).

`places.average_stay_minutes` 에 값이 있으면 그 값을 우선하고, 없을 때만 이 표를
본다. 오름·체험은 실제 체류가 길고 카페는 짧아, 단일 60분보다 카테고리별 기본값이
일정 조립(이동·식사 슬롯 배치)에 더 맞다.
"""

DEFAULT_STAY_MINUTES = 60

DEFAULT_STAY_MINUTES_BY_CATEGORY: dict[str, int] = {
    "oreum": 90,
    "walking_trail": 60,
    "beach": 60,
    "attraction": 60,
    "rental_experience": 90,
    "cafe": 50,
    "restaurant": 60,
    "restaurant_cafe": 60,
}


def default_stay_minutes(category: str | None) -> int:
    """카테고리 기본 체류시간. 표에 없으면 60분."""

    return DEFAULT_STAY_MINUTES_BY_CATEGORY.get(category or "", DEFAULT_STAY_MINUTES)
