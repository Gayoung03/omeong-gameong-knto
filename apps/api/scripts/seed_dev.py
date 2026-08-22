"""개발용 씨앗 데이터.

DB에 화면을 확인할 최소한의 데이터를 심는다.
여러 번 실행해도 중복이 쌓이지 않는다 (이미 있으면 건너뛴다).

실행:
    cd apps/api && uv run python -m scripts.seed_dev
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.api.dependencies import DEV_USER_ID
from app.db.models import Pet, Place, Route, RouteDay, RouteItem, RoutePet, User
from app.db.models.enums import (
    PetSize,
    PetSpecies,
    PlaceEnvironment,
    RouteCreationType,
    RouteStatus,
    ScheduleItemType,
    TransportType,
    TripPace,
)
from app.db.session import SessionLocal

KST = timezone(timedelta(hours=9))

# 팀원 A와 공유한 고정 값. 바꾸지 말 것.
# 사용자 id 의 정본은 app/api/dependencies.py 다 — get_current_user 가
# 이 사용자를 돌려주므로 값이 어긋나면 로컬에서 401 이 난다.
SEED_USER_ID = DEV_USER_ID
SEED_USER_EMAIL = "seed@omeong.local"

SEED_PET_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")
SEED_ROUTE_ID = uuid.UUID("00000000-0000-0000-0000-000000000201")

# 프론트 목데이터(trips.mock.ts)와 같은 이름·좌표를 쓴다.
# API를 붙였을 때 화면이 목데이터일 때와 같아야 연결을 눈으로 확인하기 쉽다.
SEED_PLACES = [
    {
        "key": "hyeopjae",
        "id": uuid.UUID("00000000-0000-0000-0000-000000000101"),
        "name": "협재해수욕장",
        "category": "attraction",
        "region": "제주시",
        "address": "제주시 한림읍",
        "latitude": Decimal("33.3939"),
        "longitude": Decimal("126.2396"),
        "description": "에메랄드빛 바다와 하얀 모래사장, 반려견 동반 산책이 가능한 해변",
        "environment": PlaceEnvironment.OUTDOOR,
        "average_stay_minutes": 90,
    },
    {
        "key": "aewol_cafe",
        "id": uuid.UUID("00000000-0000-0000-0000-000000000102"),
        "name": "애월 카페거리",
        "category": "cafe",
        "region": "제주시",
        "address": "제주시 애월읍",
        "latitude": Decimal("33.4636"),
        "longitude": Decimal("126.3096"),
        "description": "오션뷰 카페에서 여유로운 브런치 타임",
        "environment": PlaceEnvironment.MIXED,
        "average_stay_minutes": 60,
    },
    {
        "key": "hallim_park",
        "id": uuid.UUID("00000000-0000-0000-0000-000000000103"),
        "name": "한림공원",
        "category": "attraction",
        "region": "제주시",
        "address": "제주시 한림읍",
        "latitude": Decimal("33.3894"),
        "longitude": Decimal("126.2408"),
        "description": "다양한 테마 정원 산책",
        "environment": PlaceEnvironment.OUTDOOR,
        "average_stay_minutes": 120,
    },
    {
        "key": "seongsan_stay",
        "id": uuid.UUID("00000000-0000-0000-0000-000000000104"),
        "name": "숲 게스트하우스 성산점",
        "category": "accommodation",
        "region": "서귀포시",
        "address": "서귀포시 성산읍",
        "latitude": Decimal("33.4602"),
        "longitude": Decimal("126.9312"),
        "description": "반려동물과 함께 묵을 수 있는 조용한 게스트하우스",
        "environment": PlaceEnvironment.INDOOR,
        "average_stay_minutes": None,
    },
]

# 여행 하나 = 날짜 3개, 날짜마다 일정 여러 개. (routes 1:N route_days 1:N route_items)
SEED_DAYS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000211"),
        "day_number": 1,
        "route_date": date(2026, 9, 11),
        "title": "협재 바다 산책",
        "items": [
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000221"),
                "place": "hyeopjae",
                "item_type": ScheduleItemType.ATTRACTION,
                "sort_order": 0,
                "starts_at": time(10, 0),
                "stay_minutes": 90,
                "note": "모래 놀이 후 발 씻길 물티슈 챙기기",
            },
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000222"),
                "place": "aewol_cafe",
                "item_type": ScheduleItemType.CAFE,
                "sort_order": 1,
                "starts_at": time(13, 0),
                "stay_minutes": 60,
                "note": None,
            },
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000223"),
                "place": "seongsan_stay",
                "item_type": ScheduleItemType.ACCOMMODATION,
                "sort_order": 2,
                "starts_at": time(18, 0),
                "stay_minutes": None,
                "note": "체크인 18시 이후",
            },
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000212"),
        "day_number": 2,
        "route_date": date(2026, 9, 12),
        "title": "한림공원 나들이",
        "items": [
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000224"),
                "place": "hallim_park",
                "item_type": ScheduleItemType.ATTRACTION,
                "sort_order": 0,
                "starts_at": time(10, 0),
                "stay_minutes": 120,
                "note": "입구에서 반려동물 동반 확인",
            },
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000225"),
                "place": "aewol_cafe",
                "item_type": ScheduleItemType.CAFE,
                "sort_order": 1,
                "starts_at": time(15, 0),
                "stay_minutes": 60,
                "note": None,
            },
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000213"),
        "day_number": 3,
        "route_date": date(2026, 9, 13),
        "title": "마지막 바다 인사",
        "items": [
            {
                "id": uuid.UUID("00000000-0000-0000-0000-000000000226"),
                "place": "hyeopjae",
                "item_type": ScheduleItemType.ATTRACTION,
                "sort_order": 0,
                "starts_at": time(9, 0),
                "stay_minutes": 90,
                "note": None,
            },
        ],
    },
]


def _warn_if_changed(label: str, field: str, actual: object, expected: object) -> None:
    """이미 심어둔 행이 씨앗과 달라졌으면 알린다. 여러 번 돌려도 같은 데이터임을 보장."""
    if actual != expected:
        print(f"  \u26a0 {label}.{field} 가 씨앗과 다릅니다: {actual!r} (기대 {expected!r})")


def seed_user(db: Session) -> User:
    """씨앗 사용자 한 명. 이미 있으면 그대로 돌려준다."""
    user = db.get(User, SEED_USER_ID)
    if user is not None:
        _warn_if_changed("user", "nickname", user.nickname, "율무")
        _warn_if_changed("user", "email", user.email, SEED_USER_EMAIL)
        print(f"  사용자   건너뜀 ({user.nickname})")
        return user

    user = User(
        id=SEED_USER_ID,
        email=SEED_USER_EMAIL,
        nickname="율무",
    )
    db.add(user)
    db.flush()
    print(f"  사용자   생성 ({user.nickname})")
    return user


def seed_pet(db: Session, user: User) -> Pet:
    """반려동물 한 마리. 외래키(user_id)는 N쪽인 pets 에 있다."""
    pet = db.get(Pet, SEED_PET_ID)
    if pet is not None:
        _warn_if_changed("pet", "name", pet.name, "몽이")
        _warn_if_changed("pet", "species", pet.species, PetSpecies.DOG)
        print(f"  반려동물 건너뜀 ({pet.name})")
        return pet

    pet = Pet(
        id=SEED_PET_ID,
        user_id=user.id,
        name="몽이",
        species=PetSpecies.DOG,
        # species 가 dog 이므로 species_detail 은 비워야 한다 (DB 제약).
        breed="몰티즈",
        size=PetSize.SMALL,
        is_primary=True,
    )
    db.add(pet)
    db.flush()
    print(f"  반려동물 생성 ({pet.name})")
    return pet


def seed_places(db: Session) -> dict[str, Place]:
    """공식 장소들. 외래키가 없는 독립 목록이다."""
    places: dict[str, Place] = {}
    created = 0

    for spec in SEED_PLACES:
        data = dict(spec)
        key = data.pop("key")

        place = db.get(Place, data["id"])
        if place is not None:
            _warn_if_changed(f"place[{key}]", "name", place.name, data["name"])
        if place is None:
            place = Place(**data)
            db.add(place)
            created += 1

        places[key] = place

    db.flush()
    print(f"  장소     {created}개 생성 / {len(places) - created}개 건너뜀")
    return places


def seed_route(db: Session, user: User, pet: Pet, places: dict[str, Place]) -> Route:
    """여행 하나 + 날짜 + 일정. 여행이 이미 있으면 통째로 건너뛴다."""
    route = db.get(Route, SEED_ROUTE_ID)
    if route is not None:
        print(f"  여행     건너뜀 ({route.title})")
        return route

    route = Route(
        id=SEED_ROUTE_ID,
        user_id=user.id,
        title="몽이와 떠나는 제주 여행",
        status=RouteStatus.SAVED,
        # manual 이면 route_request_id 가 없어야 한다 (DB 제약).
        creation_type=RouteCreationType.MANUAL,
        start_at=datetime(2026, 9, 11, 9, 0, tzinfo=KST),
        end_at=datetime(2026, 9, 13, 18, 0, tzinfo=KST),
        pace=TripPace.RELAXED,
        transport=TransportType.RENTAL_CAR,
        style_keywords=["바다", "카페", "산책로", "자연"],
        memo="바다 산책을 좋아하는 몽이를 위한 여유로운 코스",
    )
    db.add(route)
    db.flush()

    # N:M — "이 루트에 이 반려동물이 함께 간다"
    db.add(RoutePet(route_id=route.id, pet_id=pet.id))

    item_count = 0
    for day_spec in SEED_DAYS:
        day = RouteDay(
            id=day_spec["id"],
            route_id=route.id,
            day_number=day_spec["day_number"],
            route_date=day_spec["route_date"],
            title=day_spec["title"],
        )
        db.add(day)
        db.flush()

        for item_spec in day_spec["items"]:
            starts_at = datetime.combine(day.route_date, item_spec["starts_at"], tzinfo=KST)
            stay_minutes = item_spec["stay_minutes"]
            ends_at = starts_at + timedelta(minutes=stay_minutes) if stay_minutes else None

            db.add(
                RouteItem(
                    id=item_spec["id"],
                    route_day_id=day.id,
                    place_id=places[item_spec["place"]].id,
                    item_type=item_spec["item_type"],
                    sort_order=item_spec["sort_order"],
                    starts_at=starts_at,
                    ends_at=ends_at,
                    stay_minutes=stay_minutes,
                    note=item_spec["note"],
                )
            )
            item_count += 1

    db.flush()
    print(f"  여행     생성 ({route.title}) — {len(SEED_DAYS)}일 / 일정 {item_count}개")
    return route


def main() -> None:
    print("씨앗 데이터 심는 중...")
    with SessionLocal() as db:
        user = seed_user(db)
        pet = seed_pet(db, user)
        places = seed_places(db)
        seed_route(db, user, pet, places)
        db.commit()
    print("완료")


if __name__ == "__main__":
    main()
