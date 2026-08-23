"""테스트 공용 준비물.

## DB 테스트를 왜 건너뛸 수 있게 만들었나

이 프로젝트의 모델은 PostgreSQL 전용이다(UUID·ARRAY·pgvector). SQLite 로
흉내 낼 수 없어서 진짜 PostgreSQL 이 있어야 한다. 그런데 CI(api-ci.yml)에는
아직 DB 서비스가 없다.

그래서 **`TEST_DATABASE_URL` 이 있을 때만** DB 테스트를 돌린다. 없으면 건너뛴다.
`settings.database_url` 을 몰래 갖다 쓰지 않는 것이 중요하다 — 그 값은 지금
**공유 AWS RDS** 를 가리킬 수 있고, 그러면 테스트가 팀 데이터를 건드린다.
"진짜 지우려는 DB 주소"를 사람이 직접 적어야만 돌아가게 해뒀다.

```bash
# 로컬 PostgreSQL(make dev-local)로 돌릴 때
TEST_DATABASE_URL=postgresql+psycopg://omeong:omeong@localhost:5432/omeong uv run pytest
```

## 남기지 않는다

테스트마다 바깥에 트랜잭션을 하나 열고 끝나면 통째로 롤백한다.
엔드포인트 안의 `db.commit()` 은 SAVEPOINT 로 잡혀서, 코드는 평소처럼
커밋하지만 DB 에는 아무것도 남지 않는다.
"""

import os
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_optional_user
from app.db.models import Place, Route, RouteDay, RouteItem, User
from app.db.models.enums import (
    RouteCreationType,
    RouteStatus,
    ScheduleItemType,
    TransportType,
    TripPace,
)
from app.db.session import get_db
from app.main import app

KST = timezone(timedelta(hours=9))


@pytest.fixture(scope="session")
def engine() -> Engine:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL 이 없어 DB 테스트를 건너뜁니다")
    return create_engine(url, connect_args={"options": "-c timezone=Asia/Seoul"})


@pytest.fixture
def db(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    # join_transaction_mode="create_savepoint" — 세션 안의 commit() 이 바깥
    # 트랜잭션을 끝내지 않고 SAVEPOINT 만 풀게 한다.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def _make_user(db: Session, nickname: str) -> User:
    user = User(id=uuid.uuid4(), nickname=nickname, email=f"{uuid.uuid4().hex}@test.local")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def owner(db: Session) -> User:
    return _make_user(db, "테스트주인")


@pytest.fixture
def stranger(db: Session) -> User:
    return _make_user(db, "남")


@pytest.fixture
def place(db: Session) -> Place:
    place = Place(
        id=uuid.uuid4(),
        name="테스트 해변",
        category="attraction",
        latitude=33.3939,
        longitude=126.2396,
    )
    db.add(place)
    db.flush()
    return place


@pytest.fixture
def trip(db: Session, owner: User) -> Route:
    """3일짜리 수동 여행 하나. 1일차에 항목 3개.

    `manual` 로 만든 이유는 routes 의 CheckConstraint 때문이다 —
    `recommended` 는 route_request_id 가 반드시 있어야 한다.
    """
    start = datetime(2026, 9, 11, 9, 0, tzinfo=KST)
    route = Route(
        id=uuid.uuid4(),
        user_id=owner.id,
        title="몽이랑 제주",
        status=RouteStatus.GENERATED,
        creation_type=RouteCreationType.MANUAL,
        start_at=start,
        end_at=start + timedelta(days=2),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
    )
    db.add(route)
    db.flush()

    day = RouteDay(id=uuid.uuid4(), route_id=route.id, day_number=1, route_date=start.date())
    db.add(day)
    db.flush()

    for order, name in enumerate(["협재해수욕장", "애월 카페", "숙소"]):
        db.add(
            RouteItem(
                id=uuid.uuid4(),
                route_day_id=day.id,
                item_type=ScheduleItemType.CUSTOM,
                custom_place_name=name,
                sort_order=order,
            )
        )
    db.flush()
    return route


@pytest.fixture
def client(db: Session, owner: User) -> Generator[TestClient, None, None]:
    """`owner` 로 로그인한 것처럼 동작하는 클라이언트.

    get_current_user 를 갈아끼우는 방식은 인증 담당(가영님)과 합의된 것이다.
    인증이 실제 JWT 로 바뀌어도 이 테스트는 그대로 돈다.
    """
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    # 장소·리뷰 조회는 인증이 "선택"이라 별도 의존성을 쓴다. 이것도 갈아끼우지
    # 않으면 그 엔드포인트들만 개발용 고정 사용자로 동작해서, 즐겨찾기를 눌러도
    # isFavorite 가 false 로 나온다.
    app.dependency_overrides[get_optional_user] = lambda: owner

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
