"""장소 취향 벡터의 표준 태그 순서.

엔진 내부 표준 태그는 **DB place_tags.code(영문)** 로 통일한다. `place_tags.name`
컬럼이 한글 라벨이고 `place_tags` 링크·후보 tags 도 모두 코드로 내려오므로, 점수화
(`scoring.preference_score`)와 다양성 판정(`itinerary._diversity_group`)이 같은 어휘를
써야 교집합이 실제로 잡힌다. 앱은 화면 라벨(한글)을 보내므로 경계에서 코드로 옮긴다.
"""

from collections.abc import Sequence

# place_tags.code 7종(id 29~35)과 순서를 맞춘다.
STANDARD_TAGS: tuple[str, ...] = (
    "sea",
    "cafe",
    "walk",
    "photo_spot",
    "experience",
    "rest",
    "indoor_tourism",
)

STANDARD_TAG_SET = frozenset(STANDARD_TAGS)

# 코드 → 한글 라벨(place_tags.name). 앱 표기·LLM 도구 힌트에서 코드↔한글을 잇는 데 쓴다.
TAG_LABELS: dict[str, str] = {
    "sea": "바다",
    "cafe": "카페",
    "walk": "산책",
    "photo_spot": "포토스팟",
    "experience": "체험",
    "rest": "휴식",
    "indoor_tourism": "실내관광",
}

# 모바일 화면 라벨(묶음 표현) → 코드. 앱이 실제로 보내는 살아있는 계약.
APP_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "바다·해변": ("sea",),
    "산책·공원": ("walk",),
    "실내 관광": ("indoor_tourism",),
    "오름·자연": ("rest",),
    "맛집": ("category:restaurant",),
    "문화·전시": ("indoor_tourism",),
}

# 과거에 한글 라벨(place_tags.name)로 저장된 preferred_tags 행 호환용.
# 저장분을 코드로 마이그레이션하면 통째로 제거할 수 있는 후보다.
LEGACY_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "바다": ("sea",),
    "카페": ("cafe",),
    "산책": ("walk",),
    "포토스팟": ("photo_spot",),
    "체험": ("experience",),
    "휴식": ("rest",),
    "실내관광": ("indoor_tourism",),
}

# 정규화는 두 별칭 표를 합쳐서 본다.
PREFERENCE_ALIASES: dict[str, tuple[str, ...]] = {
    **APP_LABEL_ALIASES,
    **LEGACY_LABEL_ALIASES,
}

# 순서를 강조하는 소비자가 쓸 수 있는 명시적 별칭.
TAG_ORDER = STANDARD_TAGS


def tag_hint_text() -> str:
    """LLM 도구 설명용 '코드=한글' 힌트. 코드 enum 에 의미를 붙여 한글 요청문을 매핑하게 돕는다."""
    return ", ".join(f"{code}={TAG_LABELS[code]}" for code in STANDARD_TAGS)


def normalize_preferred_tags(values: Sequence[str]) -> list[str]:
    """화면 라벨·한글 표준 라벨·이미 표준화된 코드를 중복 없이 내부 코드로 바꾼다.

    이미 영문 코드로 온 값(`sea` 등)과 `category:restaurant` 예외는 별칭에 없으므로
    그대로 통과한다. 앱이 한글 라벨을 보내는 현재 계약을 유지하되 결과는 코드가 된다.
    """

    normalized: list[str] = []
    for value in values:
        normalized.extend(PREFERENCE_ALIASES.get(value, (value,)))
    return list(dict.fromkeys(normalized))
