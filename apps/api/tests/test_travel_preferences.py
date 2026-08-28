"""여행 취향 upsert 서비스 테스트.

아직 이 서비스를 부르는 엔드포인트가 없으므로(Phase 3 의 가입·`PUT
/users/me/travel-preference` 가 쓸 예정), 죽은 코드가 되지 않게 서비스를 db
픽스처로 직접 호출해 생성/갱신/부분 갱신을 검증한다.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import User, UserTravelPreference
from app.db.models.enums import TransportType, TripPace
from app.services.travel_preferences import upsert_travel_preference


def _count_rows(db: Session, user_id) -> int:
    return db.scalar(
        select(func.count())
        .select_from(UserTravelPreference)
        .where(UserTravelPreference.user_id == user_id)
    )


def test_행이_없으면_생성한다(db: Session, owner: User) -> None:
    preference = upsert_travel_preference(
        db,
        owner.id,
        {
            "default_pace": TripPace.RELAXED,
            "default_transport": TransportType.RENTAL_CAR,
            "departure_location": "제주공항",
            "preferred_duration_days": 3,
            "companion_count": 2,
            "preferred_tags": ["바다", "숲"],
        },
    )

    assert preference.user_id == owner.id
    assert preference.default_pace is TripPace.RELAXED
    assert preference.default_transport is TransportType.RENTAL_CAR
    assert preference.departure_location == "제주공항"
    assert preference.preferred_duration_days == 3
    assert preference.companion_count == 2
    assert preference.preferred_tags == ["바다", "숲"]
    assert _count_rows(db, owner.id) == 1


def test_companion_count를_안_주면_서버_기본값_1이_된다(db: Session, owner: User) -> None:
    preference = upsert_travel_preference(db, owner.id, {"default_pace": TripPace.NORMAL})
    db.refresh(preference)

    assert preference.companion_count == 1


def test_있으면_같은_행을_갱신한다(db: Session, owner: User) -> None:
    upsert_travel_preference(
        db,
        owner.id,
        {"default_pace": TripPace.RELAXED, "companion_count": 2},
    )

    updated = upsert_travel_preference(
        db,
        owner.id,
        {"default_pace": TripPace.PACKED, "companion_count": 4},
    )

    assert updated.default_pace is TripPace.PACKED
    assert updated.companion_count == 4
    # 새 행을 만들지 않고 기존 행을 고친다.
    assert _count_rows(db, owner.id) == 1


def test_부분_갱신은_보낸_필드만_바꾼다(db: Session, owner: User) -> None:
    upsert_travel_preference(
        db,
        owner.id,
        {
            "default_pace": TripPace.RELAXED,
            "departure_location": "제주공항",
            "companion_count": 2,
            "preferred_tags": ["바다"],
        },
    )

    # departure_location 하나만 갱신한다.
    updated = upsert_travel_preference(db, owner.id, {"departure_location": "서귀포"})

    assert updated.departure_location == "서귀포"
    # 나머지는 그대로 유지된다.
    assert updated.default_pace is TripPace.RELAXED
    assert updated.companion_count == 2
    assert updated.preferred_tags == ["바다"]
    assert _count_rows(db, owner.id) == 1
