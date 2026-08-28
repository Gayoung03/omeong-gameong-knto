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

# 모바일 입력 라벨을 DB의 추천 태그/장소 유형 계약으로 옮긴다.
PREFERENCE_ALIASES: dict[str, tuple[str, ...]] = {
    "바다·해변": ("바다",),
    "산책·공원": ("산책",),
    "실내 관광": ("실내관광",),
    "오름·자연": ("휴식",),
    "맛집": ("category:restaurant",),
    "문화·전시": ("실내관광",),
}

# 순서를 강조하는 소비자가 쓸 수 있는 명시적 별칭.
TAG_ORDER = STANDARD_TAGS


def normalize_preferred_tags(values: list[str]) -> list[str]:
    """화면 라벨과 이미 표준화된 태그를 중복 없이 내부 값으로 바꾼다."""

    normalized: list[str] = []
    for value in values:
        normalized.extend(PREFERENCE_ALIASES.get(value, (value,)))
    return list(dict.fromkeys(normalized))
