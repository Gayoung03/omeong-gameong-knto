"""장소 목록·상세에 붙는 계산값들.

리뷰수·저장수·평점·즐겨찾기 여부·거리는 전부 DB 컬럼이 아니다. 매번 세어야 한다.
장소마다 따로 세면 20개짜리 목록 하나에 쿼리가 80번 나간다(N+1). 그래서
**목록 쿼리 한 줄에 상관 서브쿼리로 얹어서** 한 번에 받아온다.

거리는 PostGIS 없이 하버사인(대권거리) 공식을 SQL 로 쓴다. 지구를 완전한 구로
보는 근사라 오차가 있지만, 제주도 안에서 "가까운 순"을 정하는 데는 충분하다.
좌표는 계산에만 쓰고 저장하지 않는다(DB 문서의 GPS 정책).
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import Float, Select, Text, and_, cast, exists, func, literal, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import (
    Favorite,
    Place,
    PlacePetPolicy,
    PlaceTag,
    PlaceTagLink,
    Review,
    User,
)
from app.db.models.enums import PetPolicyType

EARTH_RADIUS_METERS = 6371000


def review_count_expr() -> ColumnElement[int]:
    return (
        select(func.count(Review.id))
        .where(Review.place_id == Place.id)
        .correlate(Place)
        .scalar_subquery()
    )


def rating_expr() -> ColumnElement[float | None]:
    return (
        select(func.round(func.avg(Review.rating), 1).cast(Float))
        .where(Review.place_id == Place.id)
        .correlate(Place)
        .scalar_subquery()
    )


def saved_count_expr() -> ColumnElement[int]:
    return (
        select(func.count())
        .select_from(Favorite)
        .where(Favorite.place_id == Place.id)
        .correlate(Place)
        .scalar_subquery()
    )


def _stored_policy_type() -> ColumnElement[str | None]:
    """이 장소에 저장된 동반정책 값. 없으면 NULL.

    **text 로 캐스팅해서 꺼낸다.** policy_type 은 PostgreSQL enum 이고 우리가
    비교·보충에 쓰는 값은 문자열이라, 그대로 두면
    `COALESCE types pet_policy_type and character varying cannot be matched`
    가 난다. enum 은 자기 타입끼리만 섞인다.
    """
    return (
        select(cast(PlacePetPolicy.policy_type, Text))
        .where(PlacePetPolicy.place_id == Place.id)
        .correlate(Place)
        .limit(1)
        .scalar_subquery()
    )


def policy_type_expr() -> ColumnElement[str]:
    """정책 행이 없는 장소도 `unknown` 으로 내린다.

    place_pet_policies 는 장소당 0~1 행이다(UNIQUE 는 아니고 인덱스만 있다).
    행이 없으면 NULL 이 나오는데, 앱은 5종 중 하나를 항상 기대하므로 여기서 메운다.
    """
    return func.coalesce(_stored_policy_type(), cast(literal(PetPolicyType.UNKNOWN.value), Text))


def is_favorite_expr(user: User | None) -> ColumnElement[bool]:
    """비로그인이면 항상 false. 명세가 그렇게 정해뒀다."""
    if user is None:
        return literal(False)
    return exists(
        select(literal(1))
        .select_from(Favorite)
        .where(Favorite.place_id == Place.id, Favorite.user_id == user.id)
        .correlate(Place)
    )


def distance_expr(latitude: float, longitude: float) -> ColumnElement[float]:
    """하버사인 거리(미터).

    `least(1, ...)` 로 감싼 이유 — 부동소수점 오차로 코사인 값이 1을 아주 살짝
    넘으면 acos 가 정의역을 벗어나 에러가 난다. 같은 좌표를 조회할 때 실제로 난다.
    """
    cosine = (
        func.cos(func.radians(latitude))
        * func.cos(func.radians(Place.latitude))
        * func.cos(func.radians(Place.longitude) - func.radians(longitude))
        + func.sin(func.radians(latitude)) * func.sin(func.radians(Place.latitude))
    )
    return EARTH_RADIUS_METERS * func.acos(func.least(1, cosine))


def has_tag_condition(tag_code: str) -> ColumnElement[bool]:
    """태그 하나를 가진 장소인가. 여러 개면 이 조건을 여러 번 AND 로 건다."""
    return exists(
        select(literal(1))
        .select_from(PlaceTagLink)
        .join(PlaceTag, PlaceTag.id == PlaceTagLink.tag_id)
        .where(PlaceTagLink.place_id == Place.id, PlaceTag.code == tag_code)
        .correlate(Place)
    )


def pet_policy_condition(policy_types: Sequence[PetPolicyType]) -> ColumnElement[bool]:
    """동반정책 필터.

    `unknown` 을 고른 경우 **정책 행이 아예 없는 장소도 포함**해야 한다.
    그 장소들이 응답에서 unknown 으로 나가기 때문이다. 값만 비교하면
    "화면에는 정보 없음이라고 떠 있는데 정보 없음 필터에는 안 잡히는" 일이 생긴다.
    """
    values = [policy.value for policy in policy_types]
    stored = _stored_policy_type()
    matched = stored.in_(values)
    if PetPolicyType.UNKNOWN in policy_types:
        return or_(matched, stored.is_(None))
    return and_(matched)


def tags_of(db: Session, place_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    """이 페이지에 실린 장소들의 태그를 한 번에 가져온다."""
    if not place_ids:
        return {}

    rows = db.execute(
        select(PlaceTagLink.place_id, PlaceTag.code)
        .join(PlaceTag, PlaceTag.id == PlaceTagLink.tag_id)
        .where(PlaceTagLink.place_id.in_(place_ids))
        .order_by(PlaceTag.code)
    ).all()

    grouped: dict[uuid.UUID, list[str]] = {}
    for place_id, code in rows:
        grouped.setdefault(place_id, []).append(code)
    return grouped


def with_computed_columns(statement: Select, user: User | None) -> Select:
    """목록 쿼리에 계산값 열을 붙인다."""
    return statement.add_columns(
        review_count_expr().label("review_count"),
        rating_expr().label("rating"),
        saved_count_expr().label("saved_count"),
        policy_type_expr().label("pet_policy_type"),
        is_favorite_expr(user).label("is_favorite"),
    )
