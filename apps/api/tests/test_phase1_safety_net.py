"""인증 Phase 1 안전망·보안 선행 작업 통합 테스트.

- 422 응답에서 입력값 에코(`input`·`ctx`)가 사라지는가
- 남의 개인 장소를 리뷰·일정·기록이 일괄 404 로 막는가
- 전역 IntegrityError 핸들러가 unique 위반을 409 로 바꾸고 내부를 숨기는가
- Settings.secret_key 가 기본값 없는 필수 필드인가
"""

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Place, RouteDay, User


def _make_private_place(db: Session, owner: User) -> Place:
    place = Place(
        id=uuid.uuid4(),
        name="남의 단골 카페",
        category="cafe",
        latitude=33.4996,
        longitude=126.5312,
        created_by_user_id=owner.id,
    )
    db.add(place)
    db.flush()
    return place


# ---------------------------------------------------------------------------
# 422 입력값 에코 제거
# ---------------------------------------------------------------------------


def test_422_응답에_입력값_에코가_없다(client: TestClient, place: Place) -> None:
    # rating 은 1~5 인데 범위를 벗어난 값을 보낸다. 기본 FastAPI 라면 에러 항목에
    # input(=999)·ctx 가 그대로 돌아온다.
    response = client.post(f"/api/v1/places/{place.id}/reviews", json={"rating": 999})

    assert response.status_code == 422
    body = response.json()
    # 형식은 기본과 같은 {"detail": [...]} 를 유지한다.
    assert isinstance(body["detail"], list)
    for item in body["detail"]:
        assert "input" not in item
        assert "ctx" not in item
        # 진단에 필요한 것은 남는다.
        assert "loc" in item and "msg" in item


# ---------------------------------------------------------------------------
# 장소 가시성 공용화 — 남의 개인 장소는 일괄 404
# ---------------------------------------------------------------------------


def test_남의_개인_장소에는_리뷰를_못_쓴다(
    client: TestClient, db: Session, stranger: User
) -> None:
    hidden = _make_private_place(db, stranger)

    response = client.post(f"/api/v1/places/{hidden.id}/reviews", json={"rating": 5})

    assert response.status_code == 404


def test_남의_개인_장소의_리뷰_목록도_404(
    client: TestClient, db: Session, stranger: User
) -> None:
    hidden = _make_private_place(db, stranger)

    response = client.get(f"/api/v1/places/{hidden.id}/reviews")

    assert response.status_code == 404


def test_남의_개인_장소는_일정에_못_넣는다(
    client: TestClient, db: Session, stranger: User, trip
) -> None:
    hidden = _make_private_place(db, stranger)
    day = db.scalar(select(RouteDay).where(RouteDay.route_id == trip.id))

    response = client.post(
        f"/api/v1/route-days/{day.id}/items",
        json={"itemType": "attraction", "sortOrder": 0, "placeId": str(hidden.id)},
    )

    assert response.status_code == 404


def test_남의_개인_장소로는_기록을_못_만든다(
    client: TestClient, db: Session, stranger: User
) -> None:
    hidden = _make_private_place(db, stranger)

    response = client.post(
        "/api/v1/travel-logs",
        json={
            "placeId": str(hidden.id),
            "recordedDate": date.today().isoformat(),
            "originalImageUrl": "https://cdn.test/x.jpg",
            "writingStyle": "dog_diary",
        },
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Settings.secret_key — 기본값 없는 필수 필드
# ---------------------------------------------------------------------------


def test_secret_key_는_기본값_없는_필수_필드다() -> None:
    field = Settings.model_fields["secret_key"]
    assert field.is_required()


# ---------------------------------------------------------------------------
# 전역 IntegrityError 핸들러
# ---------------------------------------------------------------------------


def test_unique_위반은_409_로_바뀌고_내부를_숨긴다() -> None:
    import asyncio

    from sqlalchemy.exc import IntegrityError

    from app.core.error_handlers import integrity_error_handler

    class _FakeRequest:
        method = "POST"

        class url:  # noqa: N801 - Request.url.path 흉내
            path = "/api/v1/things"

    class _FakeOrig(Exception):
        sqlstate = "23505"  # unique_violation

    # SQLAlchemy IntegrityError(statement, params, orig) — statement·params 에
    # 제약명이나 테이블명이 있어도 응답에 새지 않아야 한다.
    exc = IntegrityError(
        'INSERT INTO routes (share_token) ...',
        {"share_token": "dup"},
        _FakeOrig("duplicate key value violates unique constraint \"uq_routes_share_token\""),
    )

    response = asyncio.run(integrity_error_handler(_FakeRequest(), exc))

    assert response.status_code == 409
    body = response.body.decode()
    assert "uq_routes_share_token" not in body
    assert "routes" not in body
    assert "share_token" not in body


def test_그_외_무결성_오류는_500_이고_내부를_숨긴다() -> None:
    import asyncio

    from sqlalchemy.exc import IntegrityError

    from app.core.error_handlers import integrity_error_handler

    class _FakeRequest:
        method = "POST"

        class url:  # noqa: N801
            path = "/api/v1/things"

    class _FakeOrig(Exception):
        sqlstate = "23503"  # foreign_key_violation

    exc = IntegrityError("INSERT ...", {}, _FakeOrig("fk violation on table pets"))

    response = asyncio.run(integrity_error_handler(_FakeRequest(), exc))

    assert response.status_code == 500
    assert "pets" not in response.body.decode()
