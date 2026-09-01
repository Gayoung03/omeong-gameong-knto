"""챗봇이 부르는 장소 검색.

GPT 는 우리 `places` 테이블을 볼 수 없다. 그냥 물어보면 인터넷에서 배운 지식으로
아무 카페나 지어낸다. 그래서 **답변을 만들기 전에 우리가 먼저 찾아 재료로 건네준다.**

찾는 방법은 **도구 호출 기반 SQL** 이다(설계 결정, 0장). 임베딩·pgvector 를 쓰지
않는 이유는 `"강아지 실내 동반 가능"` 과 `"반려견 출입 불가"` 가 임베딩상 거의
붙어 있어서다 — 벡터로 고르면 **동반 불가인 곳을 추천하는 사고**가 난다.

## 새로 짤 것이 거의 없다

필터 표현식은 `app/services/place_query.py` 에 이미 다 있다. 장소 목록 화면이 쓰던
것을 그대로 가져다 쓴다. 두 곳이 같은 조건을 다르게 해석하면 "앱 검색에서는 나오는데
챗봇은 못 찾는" 일이 생긴다.
"""

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Place
from app.db.models.enums import PetPolicyType, PlaceEnvironment
from app.rag.vocabulary import CATEGORIES, REGIONS, TAGS
from app.services.place_query import (
    has_tag_condition,
    pet_friendly_condition,
    pet_policy_condition,
    policy_type_expr,
    rating_expr,
    review_count_expr,
)

#: 한 번에 돌려주는 장소 수. 설계 결정 B5.
DEFAULT_LIMIT = 5
MAX_LIMIT = 10

#: 장소당 설명 길이. 설계 결정 B6 — 전문을 5개 넣으면 입력 토큰이 폭증한다.
DESCRIPTION_LENGTH = 80

#: 설명에 섞인 원본 분류 줄. 카테고리와 중복이라 토큰만 먹는다.
#: 예) "[KCISA 원본 분류] 반려동물업 > 반려동물 서비스 > 미용"
_TAXONOMY_LINE = re.compile(r"\[[^\]]*원본 분류\][^\n]*")

#: 겸업 카테고리 — `restaurant_cafe`(식당 겸 카페)는 **식당으로도 카페로도** 찾아져야 한다.
#:
#: KCISA 원본에서 `반려동물식당카페 > 카페` 하나였던 것이 우리 쪽에서 `cafe` 와
#: `restaurant_cafe` 로 갈렸다. 그대로 두면 "식당"을 물었을 때 `restaurant` 1건만
#: 걸리고 옆의 `restaurant_cafe` 15건이 통째로 빠진다(2026-08-29 팀 DB 확인).
#: 카페 질문도 14건 중 절반만 후보가 된다.
#:
#: **GPT 에게 "두 개를 넘겨라"고 가르치지 않는다.** 도구 인자는 `category` 하나로
#: 두고 여기서 넓힌다 — 판단을 모델에 맡기면 어느 날 하나만 넘긴다. 무게 비교를
#: 파이썬에서 하는 것과 같은 이유다.
#:
#: 데이터가 정리되어 `restaurant_cafe` 가 사라지면 이 표도 함께 지운다.
_CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "restaurant": ("restaurant", "restaurant_cafe"),
    "cafe": ("cafe", "restaurant_cafe"),
}

#: 카테고리를 지정하지 않은 검색에서 **빼는** 카테고리.
#:
#: `etc` 278건은 여행지가 아니라 **반려동물 인프라**다 — 동물약국 126 · 동물병원 75 ·
#: 용품 51 · 미용 26(2026-08-29 팀 DB 확인). `vocabulary.py` 에서 `etc` 를 뺀 것은
#: **모델이 `etc` 를 고를 수 없게** 한 것이지, **결과에 안 나오게** 한 것이 아니다.
#: 그래서 카테고리를 안 넘긴 검색에는 그대로 섞여 나왔다.
#:
#: `"서귀포에 강아지랑 갈 수 있는 실내 장소 있어?"` 에 챗봇이 **동물약국 두 곳**을
#: 추천한 것을 화면에서 확인했다(2026-08-29). 약국은 강아지와 놀러 가는 곳이 아니다.
#:
#: **카테고리를 집어 물으면 그때는 나온다.** 동물병원을 찾아달라는 요청은 막지 않는다 —
#: A5(의료 금지)가 "제주 동물병원을 찾아드릴 수 있다"로 빠져나가는 통로다.
_EXCLUDED_WITHOUT_CATEGORY: tuple[str, ...] = ("etc",)


def _expand_category(category: str) -> tuple[str, ...]:
    """검색에 실제로 쓸 카테고리 목록. 겸업이 있으면 함께 본다."""
    return _CATEGORY_ALIASES.get(category, (category,))


class PlaceSort(StrEnum):
    """정렬 기준.

    **거리순이 없다.** 개인위치정보를 수집하지 않기로 해서 사용자가 어디 있는지
    모른다. "내 주변" 질문에는 지역을 되물어야 한다.
    """

    RATING = "rating"
    REVIEW_COUNT = "review_count"
    NAME = "name"


@dataclass(frozen=True)
class PlaceHit:
    """GPT 에게 건네는 장소 한 곳.

    `place_id` 는 **답변에 쓰이지 않아도 반드시 들고 다닌다** — 답변이 언급한
    장소를 `referencedPlaces` 로 내려 지도에 핀을 찍을 때 쓴다.

    `review_count` 는 설계 결정 B6 의 목록에 없지만 넣었다. 평점만 주면 GPT 가
    **리뷰 한 개짜리 5.0 을 "평점 5점"이라고 소개한다.** 다섯 토큰으로 막을 수 있는
    잘못된 확신이다.
    """

    place_id: uuid.UUID
    name: str
    category: str
    region: str | None
    pet_policy_type: PetPolicyType
    rating: float | None
    review_count: int
    description: str | None


class UnknownVocabularyError(ValueError):
    """GPT 가 목록에 없는 지역·카테고리·태그를 넘겼다.

    조용히 0건을 돌려주면 GPT 는 "그런 곳이 없다"고 답한다. 실제로는 값을 잘못
    고른 것이라, 무엇이 틀렸는지 알려주고 다시 고르게 하는 편이 낫다.
    """


def _check(value: str, allowed: Sequence[str], label: str) -> None:
    if value not in allowed:
        raise UnknownVocabularyError(
            f"{label} '{value}' 는 없는 값입니다. 다음 중에서 고르세요: {', '.join(allowed)}"
        )


def _shorten(description: str | None) -> str | None:
    """설명을 한 줄로 펴서 앞부분만 남긴다."""
    if not description:
        return None

    cleaned = _TAXONOMY_LINE.sub(" ", description)
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return None
    return cleaned[:DESCRIPTION_LENGTH]


def search_places(
    db: Session,
    *,
    region: str | None = None,
    category: str | None = None,
    pet_policy: Sequence[PetPolicyType] | None = None,
    environment: PlaceEnvironment | None = None,
    tags: Sequence[str] | None = None,
    sort: PlaceSort = PlaceSort.RATING,
    limit: int = DEFAULT_LIMIT,
) -> list[PlaceHit]:
    """조건에 맞는 장소를 찾는다.

    조건은 전부 **AND** 로 걸린다. 태그를 둘 주면 둘 다 가진 장소만 나온다.

    `category` 는 **겸업까지 넓혀서** 본다 — "식당"을 물으면 식당 겸 카페도
    함께 나온다(`_CATEGORY_ALIASES`).

    **동반 불가인 곳은 인자와 무관하게 항상 빠진다**(`pet_friendly_condition`).
    `pet_policy=["not_allowed"]` 를 넘겨도 빈 결과다. `pet_policy` 는 남은 4종
    안에서 좁히는 용도다 — 지정하지 않으면 넷 다 본다.

    `category` 를 지정하지 않으면 **`etc` 를 뺀다**(`_EXCLUDED_WITHOUT_CATEGORY`).
    여행지가 아니라 동물약국·용품점이라, 안 빼면 "갈 만한 곳"에 섞여 나온다.
    """
    if region is not None:
        _check(region, REGIONS, "지역")
    if category is not None:
        _check(category, CATEGORIES, "카테고리")
    for tag in tags or []:
        _check(tag, TAGS, "태그")

    conditions = [
        Place.is_active.is_(True),
        # 사용자가 직접 등록한 장소는 그 사람에게만 보인다. 이 한 줄이 빠지면
        # 남이 등록한 장소를 챗봇이 온 세상에 추천한다(places.py 와 같은 규칙).
        Place.created_by_user_id.is_(None),
        # 동반 불가인 곳은 GPT 가 뭘 넘기든 후보에서 빠진다. 모듈 설명의
        # "동반 불가인 곳을 추천하는 사고" 를 막는 마지막 방어선이다.
        pet_friendly_condition(),
    ]
    if region is not None:
        conditions.append(Place.region == region)
    if category is not None:
        conditions.append(Place.category.in_(_expand_category(category)))
    else:
        # 카테고리를 안 집으면 여행지가 아닌 것을 뺀다. 위 주석 참고.
        conditions.append(Place.category.notin_(_EXCLUDED_WITHOUT_CATEGORY))
    if environment is not None:
        conditions.append(Place.environment == environment)
    # 지정했을 때만 더 좁힌다. 동반 불가는 위에서 이미 빠졌다.
    if pet_policy:
        conditions.append(pet_policy_condition(pet_policy))
    for tag in tags or []:
        conditions.append(has_tag_condition(tag))

    rating = rating_expr().label("rating")
    review_count = review_count_expr().label("review_count")

    statement = select(
        Place,
        rating,
        review_count,
        policy_type_expr().label("pet_policy_type"),
    ).where(*conditions)

    if sort is PlaceSort.RATING:
        # 평점이 없는 장소(리뷰 0개)는 뒤로 보낸다. 그냥 desc() 로 두면
        # PostgreSQL 이 NULL 을 가장 큰 값으로 쳐서 맨 앞에 온다.
        statement = statement.order_by(rating.desc().nullslast(), Place.name)
    elif sort is PlaceSort.REVIEW_COUNT:
        statement = statement.order_by(review_count.desc(), Place.name)
    else:
        statement = statement.order_by(Place.name)

    rows = db.execute(statement.limit(min(limit, MAX_LIMIT))).all()

    return [
        PlaceHit(
            place_id=row[0].id,
            name=row[0].name,
            category=row[0].category,
            region=row[0].region,
            pet_policy_type=PetPolicyType(row.pet_policy_type),
            rating=row.rating,
            review_count=row.review_count,
            description=_shorten(row[0].description),
        )
        for row in rows
    ]


__all__ = [
    "DEFAULT_LIMIT",
    "PlaceHit",
    "PlaceSort",
    "UnknownVocabularyError",
    "search_places",
]
