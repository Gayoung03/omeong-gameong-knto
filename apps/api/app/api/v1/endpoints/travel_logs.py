"""여행기록 엔드포인트.

여행기록은 **물리 삭제**다. `travel_logs` 에 `deleted_at` 이 없어서 users·pets 와
달리 soft delete 대상이 아니다.

삭제해도 **S3 는 부르지 않는다.** 응답 경로에 S3 를 넣으면 삭제가 느려지고,
S3 가 일시적으로 실패했을 때 "DB 는 지워졌는데 요청은 500" 인 어긋난 상태가
생긴다. 주인 없는 파일은 배치가 나중에 정리한다(docs/api/uploads.md).

생성은 **"접수했습니다" 방식**이다. 이미지 생성이 오래 걸려 끝날 때까지 붙잡고
있으면 앱 화면이 멈춘 것처럼 보인다. 그래서 행만 만들고 `202` 를 즉시 돌려준 뒤
뒷작업에서 이미지를 만든다. 앱은 `GET /{logId}/status` 로 진행을 확인한다.

뒷작업은 FastAPI 의 BackgroundTasks 로 돈다 — Redis·Celery 를 깔지 않기 위해서다.
대신 **서버를 재시작하면 진행 중이던 건이 `generating` 에 멈춘다.** 그 상태는
앱의 "다시 만들기"(`regenerate`)로 복구한다.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser
from app.db.models import Pet, Route, TravelLog, TravelLogPet, User
from app.db.models.enums import GenerationStatus, MomentMood, WritingStyle
from app.db.session import BackgroundSessionFactory, get_background_session, get_db
from app.integrations.llm.travel_log_image import generate_log_image
from app.schemas.travel_log import (
    TravelLogCompanion,
    TravelLogCreate,
    TravelLogGenerationStatus,
    TravelLogGroupsResponse,
    TravelLogItem,
    TravelLogListResponse,
    TravelLogMonthGroup,
    TravelLogMonthSummary,
    TravelLogRegenerate,
    TravelLogRouteGroup,
    TravelLogRouteSummary,
    TravelLogUpdate,
)
from app.services.notifications import add_notification, send_pushes
from app.services.place_access import load_visible_place
from app.services.route_access import load_owned_route, pets_of

router = APIRouter(prefix="/travel-logs")

DbSession = Annotated[Session, Depends(get_db)]

#: 뒷작업이 쓸 DB 연결 공장. 요청용 연결은 응답과 함께 닫혀서 못 쓴다.
OpenSession = Annotated[BackgroundSessionFactory, Depends(get_background_session)]

#: `routeId=none` 은 "여행에 속하지 않은 개별 기록만" 이라는 뜻이다.
#: UUID 자리에 들어오는 리터럴이라 파라미터를 str 로 받아 직접 가른다.
UNGROUPED = "none"

#: 그룹 하나당 콜라주 미리보기로 내려주는 기록 수(docs/api/travel-logs.md).
PREVIEW_LIMIT = 4

#: 여행 날짜는 한국 날짜로 센다. 컨테이너는 UTC 로 도는데 그대로 쓰면
#: 이른 아침·늦은 밤에 시작하는 여행의 날짜가 하루 밀린다.
KST = timezone(timedelta(hours=9))

#: 기본 정렬. 같은 날짜 안에서는 visited_at → created_at 순이다.
#: visited_at 은 비어 있을 수 있어 뒤로 보낸다.
_LOG_ORDER = (
    TravelLog.recorded_date.desc(),
    TravelLog.visited_at.desc().nullslast(),
    TravelLog.created_at.desc(),
)

_YEAR = func.extract("year", TravelLog.recorded_date).cast(Integer)
_MONTH = func.extract("month", TravelLog.recorded_date).cast(Integer)


@router.post(
    "",
    response_model=TravelLogGenerationStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="기록 생성 및 이미지 생성 시작",
)
def create_travel_log(
    payload: TravelLogCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    open_session: OpenSession,
) -> TravelLogGenerationStatus:
    """행을 만들고 **202** 를 즉시 돌려준다. 이미지는 뒷작업이 만든다."""
    if payload.recorded_date > datetime.now(KST).date():
        raise HTTPException(status_code=422, detail="기록 날짜는 미래일 수 없습니다")

    if payload.route_id is not None:
        # 없으면 404, 남의 여행이면 403. 여행 쪽과 같은 규칙을 그대로 쓴다.
        load_owned_route(db, payload.route_id, current_user)

    place_name = _resolve_place_name(db, payload.place_id, payload.place_name, current_user)

    log = TravelLog(
        user_id=current_user.id,
        route_id=payload.route_id,
        place_id=payload.place_id,
        place_name_snapshot=place_name,
        recorded_date=payload.recorded_date,
        visited_at=payload.visited_at,
        original_image_url=payload.original_image_url,
        writing_style=payload.writing_style,
        mood=payload.mood,
        generation_status=GenerationStatus.GENERATING,
        personal_message=payload.personal_message or None,
    )
    db.add(log)
    db.flush()

    if payload.pet_ids:
        _replace_companions(db, log, payload.pet_ids, current_user)

    db.commit()

    # 커밋 뒤에 예약한다. 뒷작업은 자기 DB 연결로 이 행을 다시 읽기 때문에
    # 먼저 저장돼 있어야 한다.
    background_tasks.add_task(run_image_generation, log.id, open_session)

    return TravelLogGenerationStatus(
        id=log.id, generation_status=GenerationStatus.GENERATING
    )


@router.get("", response_model=TravelLogListResponse, summary="여행기록 목록")
def list_travel_logs(
    current_user: CurrentUser,
    db: DbSession,
    route_id: Annotated[
        str | None, Query(alias="routeId", description=f"UUID 또는 `{UNGROUPED}`")
    ] = None,
    pet_ids: Annotated[
        list[uuid.UUID] | None, Query(alias="petIds", description="여러 개면 OR")
    ] = None,
    place_query: Annotated[str | None, Query(alias="placeQuery")] = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TravelLogListResponse:
    statement = select(TravelLog).where(TravelLog.user_id == current_user.id)
    statement = _apply_filters(statement, route_id, pet_ids, place_query, from_date, to_date)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0

    logs = db.scalars(
        statement
        # 기록 한 건마다 반려동물을 따로 읽으면 20건에 20번 더 왕복한다.
        .options(selectinload(TravelLog.companions))
        .order_by(*_LOG_ORDER)
        .limit(limit)
        .offset(offset)
    ).all()

    return TravelLogListResponse(
        items=[_to_item(log) for log in logs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/groups", response_model=TravelLogGroupsResponse, summary="여행·월 단위 묶음")
def list_travel_log_groups(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TravelLogGroupsResponse:
    """여행에 속한 기록은 여행 단위로, 나머지는 연·월 단위로 묶는다.

    앱이 매번 직접 묶지 않도록 서버가 그룹을 만들어 내려준다.

    그룹 키를 먼저 뽑아 페이지를 자르고, **그 페이지에 속한 그룹의 미리보기만**
    조회한다. 전체 기록을 메모리에 올려놓고 자르지 않는다.
    """
    mine = TravelLog.user_id == current_user.id

    route_rows = db.execute(
        select(
            TravelLog.route_id,
            func.count(TravelLog.id),
            func.max(TravelLog.recorded_date),
        )
        .where(mine, TravelLog.route_id.is_not(None))
        .group_by(TravelLog.route_id)
    ).all()

    month_rows = db.execute(
        select(_YEAR, _MONTH, func.count(TravelLog.id), func.max(TravelLog.recorded_date))
        .where(mine, TravelLog.route_id.is_(None))
        .group_by(_YEAR, _MONTH)
    ).all()

    # 두 종류를 한 줄에 세워 최신순으로 정렬한다. 키는 (종류, 식별자) 다.
    keys: list[tuple[date, str, object, int]] = [
        (latest, "route", route_id, count) for route_id, count, latest in route_rows
    ]
    keys += [(latest, "month", (year, month), count) for year, month, count, latest in month_rows]
    keys.sort(key=lambda row: row[0], reverse=True)

    total = len(keys)
    page = keys[offset : offset + limit]

    route_ids = [key for _, kind, key, _ in page if kind == "route"]
    months = [key for _, kind, key, _ in page if kind == "month"]
    counts = {key: count for _, _, key, count in page}

    routes = _load_routes(db, current_user, route_ids)
    route_pets = pets_of(db, list(routes.values()))
    route_previews = _previews_by_route(db, current_user, route_ids)
    month_previews = _previews_by_month(db, current_user, months)

    items: list[TravelLogRouteGroup | TravelLogMonthGroup] = []
    for _, kind, key, _count in page:
        if kind == "route":
            route = routes.get(key)
            if route is None:
                # route_id 가 남아 있는데 여행이 없을 수는 없다(FK). 그래도
                # 방어적으로 건너뛴다 — 한 건 때문에 목록 전체가 500 이 되면 안 된다.
                continue
            previews = route_previews.get(key, [])
            items.append(
                TravelLogRouteGroup(
                    route=TravelLogRouteSummary(
                        id=route.id,
                        title=route.title,
                        start_date=_to_kst_date(route.start_at),
                        end_date=_to_kst_date(route.end_at),
                        # 여행 대표 장소는 가장 최근 기록의 장소로 삼는다.
                        place_name_snapshot=(previews[0].place_name_snapshot if previews else None),
                        companions=[_pet_to_companion(pet) for pet in route_pets.get(key, [])],
                        log_count=counts[key],
                        preview_logs=[_to_item(log) for log in previews],
                    )
                )
            )
        else:
            year, month = key
            items.append(
                TravelLogMonthGroup(
                    group=TravelLogMonthSummary(
                        year=year,
                        month=month,
                        log_count=counts[key],
                        preview_logs=[_to_item(log) for log in month_previews.get(key, [])],
                    )
                )
            )

    return TravelLogGroupsResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{log_id}/status",
    response_model=TravelLogGenerationStatus,
    summary="이미지 생성 상태",
)
def get_generation_status(
    log_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> TravelLogGenerationStatus:
    """앱이 생성이 끝났는지 확인할 때 반복해서 부르는 곳.

    상세 조회(`GET /{logId}`)보다 가볍다 — 반려동물 스냅샷을 함께 읽지 않는다.
    """
    log = _load_own_log(db, log_id, current_user, with_companions=False)
    return TravelLogGenerationStatus(
        id=log.id,
        generation_status=log.generation_status,
        generated_image_url=log.generated_image_url,
    )


@router.post(
    "/{log_id}/regenerate",
    response_model=TravelLogGenerationStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="이미지 재생성",
)
def regenerate_travel_log(
    log_id: uuid.UUID,
    payload: TravelLogRegenerate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    open_session: OpenSession,
) -> TravelLogGenerationStatus:
    """같은 원본 사진으로 다시 만든다.

    `generatedImageUrl` 은 새 이미지로 덮어쓰고 `originalImageUrl` 은 그대로 둔다.
    실패해서 `failed` 로 남은 기록을 되살리는 길이기도 하다.
    """
    log = _load_own_log(db, log_id, current_user, with_companions=False)

    if payload.writing_style is not None:
        log.writing_style = payload.writing_style
    if payload.mood is not None:
        log.mood = payload.mood
    log.generation_status = GenerationStatus.GENERATING
    db.commit()

    background_tasks.add_task(run_image_generation, log.id, open_session)

    return TravelLogGenerationStatus(
        id=log.id, generation_status=GenerationStatus.GENERATING
    )


@router.get("/{log_id}", response_model=TravelLogItem, summary="여행기록 상세")
def get_travel_log(log_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> TravelLogItem:
    return _to_item(_load_own_log(db, log_id, current_user))


@router.patch("/{log_id}", response_model=TravelLogItem, summary="여행기록 수정")
def update_travel_log(
    log_id: uuid.UUID,
    payload: TravelLogUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> TravelLogItem:
    """보낸 필드만 수정한다.

    `originalImageUrl` 과 `writingStyle` 은 `TravelLogUpdate` 에 아예 없다.
    다시 만들려면 재생성을 쓴다.
    """
    log = _load_own_log(db, log_id, current_user)
    changes = payload.model_dump(exclude_unset=True)

    pet_ids = changes.pop("pet_ids", None)
    place_name = changes.pop("place_name", None)
    place_id = changes.pop("place_id", None) if "place_id" in changes else None
    representative = changes.pop("is_representative", None)

    if "recorded_date" in changes and changes["recorded_date"] > datetime.now(KST).date():
        raise HTTPException(status_code=422, detail="기록 날짜는 미래일 수 없습니다")

    for field, value in changes.items():
        setattr(log, field, value)

    if place_id is not None:
        # 남의 개인 장소로는 바꿀 수 없다 — 없는 장소와 똑같이 404 다.
        place = load_visible_place(db, place_id, current_user)
        log.place_id = place.id
        # 장소를 바꾸면 그 시점의 이름을 다시 박제한다. 이름을 함께 보냈으면
        # 그쪽을 존중한다 — 앱이 화면에 보여준 이름과 어긋나지 않게 한다.
        log.place_name_snapshot = place_name or place.name
    elif place_name is not None:
        log.place_name_snapshot = place_name

    if pet_ids is not None:
        _replace_companions(db, log, pet_ids, current_user)

    if representative is not None:
        log.is_representative = representative
        if representative:
            _demote_others(db, log)

    db.commit()
    db.refresh(log)
    return _to_item(log)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT, summary="여행기록 삭제")
def delete_travel_log(log_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> Response:
    """물리 삭제다. `travel_log_pets` 도 ON DELETE CASCADE 로 함께 지워진다.

    S3 파일은 여기서 지우지 않는다 — 모듈 docstring 참고.
    """
    log = _load_own_log(db, log_id, current_user)
    db.delete(log)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 이미지 생성 뒷작업
# ---------------------------------------------------------------------------


def run_image_generation(
    log_id: uuid.UUID, open_session: BackgroundSessionFactory
) -> None:
    """요청이 끝난 뒤 이미지를 만들고 결과를 기록한다.

    **연결을 직접 만들지 않고 넘겨받는다.** 요청용 연결은 응답과 함께 닫혀서
    쓸 수 없고, `SessionLocal` 을 곧장 부르면 테스트가 공유 RDS 를 건드린다
    (app/db/session.py 의 `get_background_session` 설명 참고).

    성공하면 `completed` 로 바꾸고 알림을 남긴다. 실패하면 `failed` 로만 바꾸고
    **행은 지우지 않는다** — 지우면 사용자가 "다시 만들기"를 누를 대상이 없어진다.
    실패 사유를 담을 컬럼이 없어 사유는 남기지 않는다(docs/api/travel-logs.md).
    """
    with open_session() as db:
        log = db.get(TravelLog, log_id)
        if log is None:
            # 생성 중에 사용자가 지웠다. 되살릴 것이 없으니 조용히 끝낸다.
            return

        try:
            log.generated_image_url = generate_log_image(
                log.original_image_url,
                WritingStyle(log.writing_style),
                MomentMood(log.mood) if log.mood else None,
                log.place_name_snapshot,
            )
        except Exception:
            # 어떤 이유로 실패했든 앱에는 "다시 만들기" 하나만 보여준다.
            log.generation_status = GenerationStatus.FAILED
            db.commit()
            return

        log.generation_status = GenerationStatus.COMPLETED
        db.commit()

        notification = add_notification(
            db,
            user_id=log.user_id,
            type="travel_log_ready",
            target_id=log.id,
            title="여행기록이 완성됐어요",
            content=f"{log.place_name_snapshot}에서의 순간이 기록으로 만들어졌어요.",
        )
        db.commit()
        send_pushes(db, notification)


# ---------------------------------------------------------------------------
# 공용
# ---------------------------------------------------------------------------


def _load_own_log(
    db: Session, log_id: uuid.UUID, user: User, *, with_companions: bool = True
) -> TravelLog:
    """없으면 404, 남의 것이면 403.

    둘을 전부 403 으로 합치면 남의 기록 id 를 찍어보며 존재 여부를 알아낼 수
    있게 된다. 명세가 둘을 나눠둔 이유다(services/route_access.py 와 같은 규칙).

    `with_companions=False` 는 상태 조회처럼 반려동물이 필요 없는 곳에서 쓴다.
    앱이 2 초마다 부르는 자리라 쓸데없는 왕복을 줄인다.
    """
    statement = select(TravelLog).where(TravelLog.id == log_id)
    if with_companions:
        statement = statement.options(selectinload(TravelLog.companions))

    log = db.scalar(statement)
    if log is None:
        raise HTTPException(status_code=404, detail="여행기록을 찾을 수 없습니다")
    if log.user_id != user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 여행기록입니다")
    return log


def _resolve_place_name(
    db: Session, place_id: uuid.UUID | None, place_name: str | None, user: User
) -> str:
    """기록에 박제할 장소명을 정한다.

    `placeId` 를 보내도 **그 시점의 장소명을 복사**한다. 장소가 나중에 삭제되거나
    이름이 바뀌어도 기록 화면이 유지된다(docs/api/travel-logs.md).

    이름을 함께 보냈으면 그쪽을 존중한다 — 앱이 화면에 보여준 이름과 어긋나지
    않게 한다. PATCH 의 장소 변경도 같은 규칙이다.

    남의 개인 장소는 없는 장소와 똑같이 404 다(장소 조회와 동일 규칙).
    """
    if place_id is not None:
        place = load_visible_place(db, place_id, user)
        return place_name or place.name

    if not place_name:
        raise HTTPException(status_code=422, detail="placeId 가 없으면 placeName 이 필요합니다")
    return place_name


def _apply_filters(
    statement,
    route_id: str | None,
    pet_ids: list[uuid.UUID] | None,
    place_query: str | None,
    from_date: date | None,
    to_date: date | None,
):
    if route_id == UNGROUPED:
        statement = statement.where(TravelLog.route_id.is_(None))
    elif route_id is not None:
        try:
            parsed = uuid.UUID(route_id)
        except ValueError as error:
            raise HTTPException(
                status_code=422, detail=f"routeId 는 UUID 또는 `{UNGROUPED}` 여야 합니다"
            ) from error
        statement = statement.where(TravelLog.route_id == parsed)

    if pet_ids:
        # 조인 대신 서브쿼리를 쓴다. 반려동물 두 마리가 함께 있는 기록이
        # 조인에서는 두 줄로 나와 total 이 부풀고 페이지가 어긋난다.
        statement = statement.where(
            TravelLog.id.in_(
                select(TravelLogPet.travel_log_id).where(TravelLogPet.pet_id.in_(pet_ids))
            )
        )

    if place_query:
        statement = statement.where(TravelLog.place_name_snapshot.ilike(f"%{place_query}%"))

    if from_date is not None:
        statement = statement.where(TravelLog.recorded_date >= from_date)
    if to_date is not None:
        statement = statement.where(TravelLog.recorded_date <= to_date)

    return statement


def _replace_companions(db: Session, log: TravelLog, pet_ids: list[uuid.UUID], user: User) -> None:
    """함께한 반려동물을 통째로 갈아끼운다.

    `(travel_log_id, pet_id)` 에 UNIQUE 가 있어 남겨둔 채 새로 넣으면 부딪친다.
    지우고 flush 한 뒤에 넣는다.

    이름·사진은 **지금 시점** 값으로 다시 박제한다. 이미 지워진 프로필은
    새로 넣지 않는다 — 살아 있는 반려동물만 고를 수 있어야 한다.
    """
    unique_ids = list(dict.fromkeys(pet_ids))
    pets = list(
        db.scalars(select(Pet).where(Pet.id.in_(unique_ids), Pet.deleted_at.is_(None))).all()
    )
    if len(pets) != len(unique_ids):
        raise HTTPException(status_code=404, detail="반려동물을 찾을 수 없습니다")
    for pet in pets:
        if pet.user_id != user.id:
            raise HTTPException(status_code=403, detail="다른 사용자의 반려동물입니다")

    log.companions.clear()
    db.flush()

    by_id = {pet.id: pet for pet in pets}
    for pet_id in unique_ids:
        pet = by_id[pet_id]
        log.companions.append(
            TravelLogPet(
                pet_id=pet.id,
                pet_name_snapshot=pet.name,
                pet_profile_image_snapshot=pet.image_url,
            )
        )
    db.flush()


def _demote_others(db: Session, log: TravelLog) -> None:
    """같은 날짜의 기존 대표를 내린다.

    "한 날짜에 대표는 하나"를 DB 제약으로 걸어두지 않아 서버가 지켜야 한다
    (docs/api/travel-logs.md PATCH 절).
    """
    db.execute(
        TravelLog.__table__.update()
        .where(
            TravelLog.user_id == log.user_id,
            TravelLog.recorded_date == log.recorded_date,
            TravelLog.id != log.id,
            TravelLog.is_representative.is_(True),
        )
        .values(is_representative=False)
    )


def _load_routes(db: Session, user: User, route_ids: list[uuid.UUID]) -> dict[uuid.UUID, Route]:
    if not route_ids:
        return {}
    routes = db.scalars(
        select(Route).where(Route.id.in_(route_ids), Route.user_id == user.id)
    ).all()
    return {route.id: route for route in routes}


def _previews_by_route(
    db: Session, user: User, route_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[TravelLog]]:
    """여행별 미리보기 기록 최대 4건.

    여행 수만큼 쿼리를 돌리지 않는다. 창 함수로 여행 안에서 순번을 매기고
    앞의 몇 건만 골라 한 번에 읽는다.
    """
    if not route_ids:
        return {}

    logs = _top_logs(db, user, TravelLog.route_id.in_(route_ids), TravelLog.route_id)

    grouped: dict[uuid.UUID, list[TravelLog]] = {route_id: [] for route_id in route_ids}
    for log in logs:
        grouped[log.route_id].append(log)
    return grouped


def _previews_by_month(
    db: Session, user: User, months: list[tuple[int, int]]
) -> dict[tuple[int, int], list[TravelLog]]:
    if not months:
        return {}

    logs = _top_logs(db, user, TravelLog.route_id.is_(None), _YEAR, _MONTH)

    grouped: dict[tuple[int, int], list[TravelLog]] = {month: [] for month in months}
    for log in logs:
        key = (log.recorded_date.year, log.recorded_date.month)
        if key in grouped:
            grouped[key].append(log)
    return grouped


def _top_logs(db: Session, user: User, condition, *partition_by) -> list[TravelLog]:
    ranked = (
        select(
            TravelLog.id,
            func.row_number()
            .over(partition_by=list(partition_by), order_by=list(_LOG_ORDER))
            .label("rank"),
        )
        .where(TravelLog.user_id == user.id, condition)
        .subquery()
    )

    return list(
        db.scalars(
            select(TravelLog)
            .where(TravelLog.id.in_(select(ranked.c.id).where(ranked.c.rank <= PREVIEW_LIMIT)))
            .options(selectinload(TravelLog.companions))
            .order_by(*_LOG_ORDER)
        ).all()
    )


def _to_kst_date(value: datetime | None) -> date | None:
    return None if value is None else value.astimezone(KST).date()


def _pet_to_companion(pet: Pet) -> TravelLogCompanion:
    """여행 자체의 반려동물을 기록의 `companions` 와 같은 모양으로 맞춘다.

    이쪽은 스냅샷이 아니라 현재 프로필이라 값은 항상 최신이다. 앱이 두 곳을
    같은 컴포넌트로 그릴 수 있게 형태만 통일한다.
    """
    return TravelLogCompanion(
        pet_id=pet.id,
        name_snapshot=pet.name,
        profile_image_snapshot=pet.image_url,
    )


def _to_item(log: TravelLog) -> TravelLogItem:
    return TravelLogItem(
        id=log.id,
        route_id=log.route_id,
        place_id=log.place_id,
        place_name_snapshot=log.place_name_snapshot,
        recorded_date=log.recorded_date,
        visited_at=log.visited_at,
        original_image_url=log.original_image_url,
        generated_image_url=log.generated_image_url,
        writing_style=log.writing_style,
        mood=log.mood,
        generation_status=log.generation_status,
        personal_message=log.personal_message,
        is_representative=log.is_representative,
        companions=[
            TravelLogCompanion(
                pet_id=companion.pet_id,
                name_snapshot=companion.pet_name_snapshot,
                profile_image_snapshot=companion.pet_profile_image_snapshot,
            )
            for companion in log.companions
        ],
        created_at=log.created_at,
    )
