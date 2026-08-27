"""장소 취향 벡터의 표준 태그 순서."""

STANDARD_TAGS: tuple[str, ...] = (
    "바다",
    "카페",
    "산책",
    "포토스팟",
    "체험",
    "휴식",
    "실내관광",
)

STANDARD_TAG_SET = frozenset(STANDARD_TAGS)

# 순서를 강조하는 소비자가 쓸 수 있는 명시적 별칭.
TAG_ORDER = STANDARD_TAGS
