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

#: 동반정책을 지정하지 않았을 때 기본으로 포함하는 값 — `not_allowed` 만 뺀다.
#:
#: GPT 가 정책을 **안 고르는 경우가 많다.** 사용자가 "애월 카페 알려줘"라고만
#: 물으면 굳이 넣을 이유가 없기 때문이다. 그때 전부 돌려주면 `not_allowed` 인
#: 곳(반려묘 전용 카페, KCISA 원본이 `동반 가능정보: N` 인 곳)이 추천에 섞인다.
#: **반려동물 앱에서 이건 검색 오류가 아니라 헛걸음시키는 사고다.**
#:
#: `unknown` 은 뺀 것이 아니라 **넣는다.** 우리 장소 데이터는 동반 가능한 곳만
#: 모은 것이라, `unknown` 은 "동반 가능 여부를 모름"이 아니라 **"동반은 되는데
#: 실내/야외 세부를 모름"** 이다(docs/planning/chatbot-design-decisions.md).
#: 빼면 절반이 사라진다.
DEFAULT_POLICIES: tuple[PetPolicyType, ...] = tuple(
    policy for policy in PetPolicyType if policy is not PetPolicyType.NOT_ALLOWED
)


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

    `pet_policy` 를 지정하지 않으면 **`not_allowed` 만 빼고** 전부 본다
    (`DEFAULT_POLICIES`). 인자를 아예 안 주면 동반 불가인 곳을 뺀 채로
    평점 높은 순 다섯 곳이 나온다.
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
    ]
    if region is not None:
        conditions.append(Place.region == region)
    if category is not None:
        conditions.append(Place.category == category)
    if environment is not None:
        conditions.append(Place.environment == environment)
    # 지정하지 않으면 `not_allowed` 만 빼고 전부 본다. 위 DEFAULT_POLICIES 참고.
    conditions.append(pet_policy_condition(pet_policy or DEFAULT_POLICIES))
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
