"""장소 조회·등록·즐겨찾기 엔드포인트.

## 공식 장소와 나만의 장소는 경로가 다르다

사용자가 등록한 장소는 별도 테이블이 아니라 `places` 에 함께 저장되고
`created_by_user_id` 로만 구분된다. 조건을 한 번만 빠뜨려도 남이 등록한 장소가
("우리 강아지 단골 카페" 같은 이름과 좌표째로) 전체 검색에 섞여 나온다.

그래서 `?includeMine=true` 같은 파라미터로 섞지 않고 **경로를 나눴다**
(docs/api/places.md 2026-08-18 확정).

| 경로 | 나오는 것 |
| --- | --- |
| `GET /places` | 공식 장소만 (`created_by_user_id IS NULL`) |
| `GET /users/me/places` | 내가 등록한 장소만 |
| 남이 등록한 장소 | 어떤 경로로도 안 나온다 |
"""

import uuid
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Row, func, null, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, OptionalUser
from app.db.models import (
    Favorite,
    Place,
    PlaceBusinessHour,
    PlacePetPolicy,
    PlaceTag,
    PlaceTagLink,
    User,
)
from app.db.models.enums import DataProvider, PetPolicyType, PlaceEnvironment
from app.db.session import get_db
from app.schemas.place import (
    BusinessHourResponse,
    FavoritePlaceItem,
    FavoritePlaceListResponse,
    PetPolicyResponse,
    PlaceCreate,
    PlaceDetail,
    PlaceListItem,
    PlaceListResponse,
    PlaceTagListResponse,
    PlaceTagResponse,
)
from app.services.place_access import load_visible_place
from app.services.place_query import (
    distance_expr,
    has_tag_condition,
    is_favorite_expr,
    pet_policy_condition,
    policy_type_expr,
    rating_expr,
    review_count_expr,
    saved_count_expr,
    tags_of,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


class PlaceSort(StrEnum):
    DISTANCE = "distance"
    NAME = "name"
    REVIEW_COUNT = "reviewCount"


def _to_list_item(row: Row, tags: list[str]) -> PlaceListItem:
    place: Place = row[0]
    distance = row.distance_meters
    return PlaceListItem(
        id=place.id,
        name=place.name,
        category=place.category,
        region=place.region,
        address=place.address,
        road_address=place.road_address,
        latitude=float(place.latitude),
        longitude=float(place.longitude),
        primary_image_url=place.primary_image_url,
        environment=place.environment,
        pet_policy_type=row.pet_policy_type,
        tags=tags,
        reservation_required=place.reservation_required,
        # 미터 단위 소수점은 의미가 없다. 앱도 "4.8km" 로 반올림해 보여준다.
        distance_meters=round(distance) if distance is not None else None,
        review_count=row.review_count,
        saved_count=row.saved_count,
        rating=row.rating,
        is_favorite=row.is_favorite,
    )


@router.get("/places", response_model=PlaceListResponse, summary="장소 목록·검색")
def list_places(
    db: DbSession,
    current_user: OptionalUser,
    q: Annotated[str | None, Query(description="장소명 검색어")] = None,
    category: str | None = None,
    region: str | None = None,
    tags: Annotated[list[str] | None, Query(description="여러 개면 AND")] = None,
    pet_policy: Annotated[list[PetPolicyType] | None, Query(alias="petPolicy")] = None,
    environment: PlaceEnvironment | None = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius: Annotated[int, Query(ge=1, description="미터. 좌표를 보낼 때만 유효")] = 3000,
    sort: PlaceSort | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PlaceListResponse:
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="latitude 와 longitude 는 함께 보내야 합니다")

    conditions = [
        Place.is_active.is_(True),
        # 이 한 줄이 빠지면 남이 등록한 장소가 검색에 섞인다. 위 문서 주석 참고.
        Place.created_by_user_id.is_(None),
    ]
    if q:
        conditions.append(Place.name.ilike(f"%{q}%"))
    if category:
        conditions.append(Place.category == category)
    if region:
        conditions.append(Place.region == region)
    if environment:
        conditions.append(Place.environment == environment)
    if pet_policy:
        conditions.append(pet_policy_condition(pet_policy))
    for tag_code in tags or []:
        conditions.append(has_tag_condition(tag_code))

    has_coordinates = latitude is not None and longitude is not None
    if has_coordinates:
        distance = distance_expr(latitude, longitude)
        conditions.append(distance <= radius)
    else:
        distance = null()

    total = db.scalar(select(func.count(Place.id)).where(*conditions)) or 0

    statement = select(
        Place,
        review_count_expr().label("review_count"),
        rating_expr().label("rating"),
        saved_count_expr().label("saved_count"),
        policy_type_expr().label("pet_policy_type"),
        is_favorite_expr(current_user).label("is_favorite"),
        distance.label("distance_meters"),
    ).where(*conditions)

    # 좌표를 보내면 가까운 순, 아니면 이름순이 기본이다(명세).
    chosen = sort or (PlaceSort.DISTANCE if has_coordinates else PlaceSort.NAME)
    if chosen is PlaceSort.DISTANCE and has_coordinates:
        statement = statement.order_by(distance)
    elif chosen is PlaceSort.REVIEW_COUNT:
        statement = statement.order_by(review_count_expr().desc(), Place.name)
    else:
        statement = statement.order_by(Place.name)

    rows = db.execute(statement.limit(limit).offset(offset)).all()
    tag_map = tags_of(db, [row[0].id for row in rows])

    return PlaceListResponse(
        items=[_to_list_item(row, tag_map.get(row[0].id, [])) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/place-tags", response_model=PlaceTagListResponse, summary="태그 목록")
def list_place_tags(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PlaceTagListResponse:
    total = db.scalar(select(func.count(PlaceTag.id))) or 0
    tags = db.scalars(select(PlaceTag).order_by(PlaceTag.code).limit(limit).offset(offset)).all()

    return PlaceTagListResponse(
        items=[PlaceTagResponse(code=tag.code, name=tag.name) for tag in tags],
        total=total,
        limit=limit,
        offset=offset,
    )


# /places/{place_id} 보다 먼저 등록한다. 순서가 뒤바뀌면 "me" 를 placeId(UUID)로
# 읽으려다 422 가 난다.
@router.get(
    "/users/me/places", response_model=PlaceListResponse, summary="내가 등록한 장소"
)
def list_my_places(
    current_user: CurrentUser,
    db: DbSession,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PlaceListResponse:
    """태그·리뷰·거리는 항상 비어 있다.

    태그는 서버가 공식 장소에만 붙이고, 내 장소에는 리뷰를 쓸 수 없으며,
    좌표 파라미터를 받지 않는다(명세).
    """
    conditions = [Place.created_by_user_id == current_user.id, Place.is_active.is_(True)]
    if q:
        conditions.append(Place.name.ilike(f"%{q}%"))

    total = db.scalar(select(func.count(Place.id)).where(*conditions)) or 0
    places = db.scalars(
        select(Place)
        .where(*conditions)
        .order_by(Place.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return PlaceListResponse(
        items=[
            PlaceListItem(
                id=place.id,
                name=place.name,
                category=place.category,
                region=place.region,
                address=place.address,
                road_address=place.road_address,
                latitude=float(place.latitude),
                longitude=float(place.longitude),
                primary_image_url=place.primary_image_url,
                environment=place.environment,
                pet_policy_type=PetPolicyType.UNKNOWN,
                tags=[],
                reservation_required=place.reservation_required,
                distance_meters=None,
                review_count=0,
                saved_count=0,
                rating=None,
                is_favorite=False,
            )
            for place in places
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/users/me/favorites",
    response_model=FavoritePlaceListResponse,
    summary="내 즐겨찾기 목록",
)
def list_my_favorites(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FavoritePlaceListResponse:
    condition = Favorite.user_id == current_user.id
    total = db.scalar(select(func.count()).select_from(Favorite).where(condition)) or 0

    rows = db.execute(
        select(
            Place,
            review_count_expr().label("review_count"),
            rating_expr().label("rating"),
            saved_count_expr().label("saved_count"),
            policy_type_expr().label("pet_policy_type"),
            is_favorite_expr(current_user).label("is_favorite"),
            null().label("distance_meters"),
            Favorite.created_at.label("favorited_at"),
        )
        .join(Favorite, Favorite.place_id == Place.id)
        .where(condition)
        .order_by(Favorite.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    tag_map = tags_of(db, [row[0].id for row in rows])

    return FavoritePlaceListResponse(
        items=[
            FavoritePlaceItem(
                **_to_list_item(row, tag_map.get(row[0].id, [])).model_dump(),
                favorited_at=row.favorited_at,
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/places/{place_id}", response_model=PlaceDetail, summary="장소 상세")
def get_place(place_id: uuid.UUID, current_user: OptionalUser, db: DbSession) -> PlaceDetail:
    place = load_visible_place(db, place_id, current_user)
    return _to_detail(db, place, current_user)


@router.post(
    "/places",
    response_model=PlaceDetail,
    status_code=status.HTTP_201_CREATED,
    summary="나만의 장소 등록",
)
def create_place(
    payload: PlaceCreate, current_user: CurrentUser, db: DbSession
) -> PlaceDetail:
    place = Place(
        name=payload.name,
        category=payload.category,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        road_address=payload.road_address,
        phone=payload.phone,
        primary_image_url=payload.primary_image_url,
        description=payload.description,
        # 출처를 앱이 정하게 두면 사용자가 등록한 장소가 관광공사 데이터인 척할 수 있다.
        description_source=DataProvider.INTERNAL,
        created_by_user_id=current_user.id,
    )
    db.add(place)
    db.commit()
    db.refresh(place)
    return _to_detail(db, place, current_user)


@router.put(
    "/places/{place_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="즐겨찾기 등록",
)
def add_favorite(place_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> Response:
    """POST 가 아니라 PUT 인 이유는 **여러 번 눌러도 결과가 같아야** 하기 때문이다.

    이미 즐겨찾기한 장소여도 409 가 아니라 204 다.
    """
    load_visible_place(db, place_id, current_user)

    existing = db.get(Favorite, {"user_id": current_user.id, "place_id": place_id})
    if existing is None:
        db.add(Favorite(user_id=current_user.id, place_id=place_id))
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/places/{place_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="즐겨찾기 해제",
)
def remove_favorite(place_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> Response:
    load_visible_place(db, place_id, current_user)

    existing = db.get(Favorite, {"user_id": current_user.id, "place_id": place_id})
    if existing is not None:
        db.delete(existing)
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 공용
# ---------------------------------------------------------------------------


def _to_detail(db: Session, place: Place, user: User | None) -> PlaceDetail:
    row = db.execute(
        select(
            review_count_expr().label("review_count"),
            rating_expr().label("rating"),
            saved_count_expr().label("saved_count"),
            is_favorite_expr(user).label("is_favorite"),
        ).where(Place.id == place.id)
    ).one()

    policy = db.scalar(select(PlacePetPolicy).where(PlacePetPolicy.place_id == place.id))
    hours = db.scalars(
        select(PlaceBusinessHour)
        .where(PlaceBusinessHour.place_id == place.id)
        .order_by(PlaceBusinessHour.day_of_week)
    ).all()
    tag_rows = db.execute(
        select(PlaceTag.code, PlaceTag.name)
        .join(PlaceTagLink, PlaceTagLink.tag_id == PlaceTag.id)
        .where(PlaceTagLink.place_id == place.id)
        .order_by(PlaceTag.code)
    ).all()

    return PlaceDetail(
        id=place.id,
        name=place.name,
        category=place.category,
        category_detail=place.category_detail,
        region=place.region,
        address=place.address,
        road_address=place.road_address,
        latitude=float(place.latitude),
        longitude=float(place.longitude),
        phone=place.phone,
        homepage_url=place.homepage_url,
        primary_image_url=place.primary_image_url,
        description=place.description,
        description_source=place.description_source,
        environment=place.environment,
        amenities=place.amenities,
        average_stay_minutes=place.average_stay_minutes,
        reservation_required=place.reservation_required,
        is_user_created=place.created_by_user_id is not None,
        tags=[PlaceTagResponse(code=code, name=name) for code, name in tag_rows],
        pet_policy=_to_pet_policy(policy),
        business_hours=[
            BusinessHourResponse(
                day_of_week=hour.day_of_week,
                opens_at=hour.opens_at,
                closes_at=hour.closes_at,
                break_start_at=hour.break_start_at,
                break_end_at=hour.break_end_at,
                is_closed=hour.is_closed,
                raw_text=hour.raw_text,
            )
            for hour in hours
        ],
        review_count=row.review_count,
        saved_count=row.saved_count,
        rating=row.rating,
        is_favorite=row.is_favorite,
    )


def _to_pet_policy(policy: PlacePetPolicy | None) -> PetPolicyResponse:
    """정책 행이 없어도 `unknown` 짜리 객체를 만들어 준다.

    null 을 내리면 앱이 매번 존재 확인을 해야 하고, 한 군데라도 빠뜨리면
    상세 화면이 통째로 깨진다. 모양을 항상 같게 유지한다.
    """
    if policy is None:
        return PetPolicyResponse(
            policy_type=PetPolicyType.UNKNOWN,
            allowed_species=None,
            allowed_sizes=None,
            max_weight_kg=None,
            carrier_required=None,
            leash_required=None,
            vaccination_required=None,
            extra_fee_amount=None,
            notes=None,
            source=None,
            source_url=None,
            verified_at=None,
            reliability_score=None,
            muzzle_required=None,
            food_area_allowed=None,
            max_pets_per_person=None,
            caution_note=None,
        )

    return PetPolicyResponse(
        policy_type=policy.policy_type,
        allowed_species=policy.allowed_species,
        allowed_sizes=policy.allowed_sizes,
        max_weight_kg=float(policy.max_weight_kg) if policy.max_weight_kg is not None else None,
        carrier_required=policy.carrier_required,
        leash_required=policy.leash_required,
        vaccination_required=policy.vaccination_required,
        extra_fee_amount=policy.extra_fee_amount,
        notes=policy.notes,
        source=policy.source,
        source_url=policy.source_url,
        verified_at=policy.verified_at,
        reliability_score=(
            float(policy.reliability_score) if policy.reliability_score is not None else None
        ),
        muzzle_required=policy.muzzle_required,
        food_area_allowed=policy.food_area_allowed,
        max_pets_per_person=policy.max_pets_per_person,
        caution_note=policy.caution_note,
    )
