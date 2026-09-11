"""시나리오 매트릭스 측정 — 권역 4 × 속도 3 × 박 1~3 = 36 (오프라인).

재설계 Phase 0/7: 현재 엔진의 실패율·슬롯 충족률·확인필요율을 권역·속도·박수별로
잰다. 외부 호출(TMAP·TourAPI·기상청·OpenAI·카카오 지오코딩)은 전부 대역으로 막고,
만든 route_requests/routes 는 **바깥 트랜잭션 롤백**으로 정리한다(아무것도 남기지 않음).

대상 DB 는 `--database-url`(기본 로컬 omeong_test). 측정은 **쓰기**(생성 후 롤백)를 하므로
**로컬 compose DB(호스트 localhost/127.0.0.1/::1/compose `postgres`)에만** 실행한다 — 그 외
호스트는 전부 거부한다(허용목록). 포워딩된 원격(Railway ssh·포트포워딩)은 localhost 로도
붙을 수 있어 허용목록으로도 못 막으니 **포워딩된 원격에는 절대 쓰지 말 것.**

    uv run python -m scripts.measure_scenarios \
        [--database-url postgresql+psycopg://omeong:omeong@localhost:5432/omeong_test] \
        [--json out.json] [--pets small|none|large]
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlsplit

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    Pet,
    Place,
    Route,
    RouteDay,
    RouteItem,
    RouteMove,
    RouteRequest,
    RouteRequestPet,
    User,
)
from app.db.models.enums import (
    PetSize,
    PetSpecies,
    RouteCreationType,
    RouteItemSlotStatus,
    RouteStatus,
    ScheduleItemType,
    TransportType,
    TripPace,
)
from app.recommend.travel_estimate import estimate_leg
from app.recommend.weights import resolve_weights
from app.services import route_recommendation as rr

KST = timezone(timedelta(hours=9))

#: 권역 대표 좌표(제주 4분면). 하드코딩 — 측정 재현성을 위해.
REGIONS: list[tuple[str, float, float]] = [
    ("제주시", 33.4996, 126.5312),
    ("서귀포", 33.2541, 126.5600),
    ("동부(성산)", 33.4586, 126.9420),
    ("서부(한림)", 33.4137, 126.2699),
]
PACES = [TripPace.RELAXED, TripPace.NORMAL, TripPace.PACKED]
NIGHTS = [1, 2, 3]
# 허용목록 — 로컬 compose DB 만. 거부목록은 Railway 포트포워딩(localhost) 을 못 막는다.
# URL 의 hostname 만 정확 일치로 본다(비밀번호·DB 이름에 "localhost" 가 섞여도 안전).
LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


def _install_offline_stubs() -> None:
    """생성 경로의 모든 외부 호출을 오프라인 대역으로 바꾼다."""
    rr._tour_api_places = lambda *_a, **_k: []  # type: ignore[assignment]
    rr.get_daily_forecasts = lambda *_a, **_k: {}  # type: ignore[assignment]
    # TMAP 대신 실측 회귀 추정식으로 이동시간을 만든다(캐시·네트워크 없음).
    rr.get_route = lambda _db, origin, dest, transport, _depart=None: estimate_leg(  # type: ignore[assignment]
        origin, dest, transport
    )
    settings.openai_api_key = ""  # generate_trip_explanation·request_intent → None


def _require_local(url: str) -> None:
    hostname = (urlsplit(url).hostname or "").lower()
    if hostname not in LOCAL_DB_HOSTS:
        raise SystemExit(
            f"거부: 대상 DB 호스트가 로컬이 아닙니다(host={hostname!r}). 측정은 쓰기를 하므로 "
            "로컬 compose DB(localhost/127.0.0.1/::1/postgres)에만 실행하세요. "
            "포워딩된 원격(Railway ssh 등)에는 쓰지 마세요."
        )


def _pet_ids(db: Session, user: User, mode: str) -> list[uuid.UUID]:
    if mode == "none":
        return []
    size = PetSize.LARGE if mode == "large" else PetSize.SMALL
    pet = Pet(
        id=uuid.uuid4(),
        user_id=user.id,
        name="측정견",
        species=PetSpecies.DOG,
        size=size,
        weight_kg=Decimal("30") if mode == "large" else Decimal("5"),
    )
    db.add(pet)
    db.flush()
    return [pet.id]


def _run_scenario(
    db: Session,
    user: User,
    region: tuple[str, float, float],
    pace: TripPace,
    nights: int,
    pet_mode: str,
) -> dict:
    name, lat, lng = region
    start = datetime(2026, 9, 21, 9, tzinfo=KST)
    end = start + timedelta(days=nights, hours=9)
    request = RouteRequest(
        id=uuid.uuid4(),
        user_id=user.id,
        start_at=start,
        end_at=end,
        pace=pace,
        transport=TransportType.RENTAL_CAR,
        companion_count=1,
        departure_latitude=Decimal(str(lat)),
        departure_longitude=Decimal(str(lng)),
        applied_weights=resolve_weights().model_dump(),
    )
    db.add(request)
    db.flush()
    for pet_id in _pet_ids(db, user, pet_mode):
        db.add(RouteRequestPet(route_request_id=request.id, pet_id=pet_id))
    route = Route(
        id=uuid.uuid4(),
        route_request_id=request.id,
        user_id=user.id,
        title=f"{name}-{pace.value}-{nights}박",
        status=RouteStatus.GENERATING,
        creation_type=RouteCreationType.RECOMMENDED,
        version=1,
        start_at=start,
        end_at=end,
        pace=pace,
        transport=TransportType.RENTAL_CAR,
    )
    db.add(route)
    db.flush()

    started = time.perf_counter()
    error: str | None = None
    try:
        rr.generate_route(db, route.id)
    except rr.RecommendationGenerationError as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 — 측정은 어떤 실패도 기록만 하고 계속 간다
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

    db.refresh(route)
    metrics = _measure(db, route.id)
    return {
        "region": name,
        "pace": pace.value,
        "nights": nights,
        "status": "failed" if error else route.status.value,
        "error": error,
        "elapsed_ms": elapsed_ms,
        **metrics,
    }


def _measure(db: Session, route_id: uuid.UUID) -> dict:
    """방문 슬롯 집계(앵커 제외)와 하루 이동시간 합(추정)."""
    rows = list(
        db.execute(
            select(RouteItem.slot_status, func.count())
            .join(RouteDay, RouteDay.id == RouteItem.route_day_id)
            .where(
                RouteDay.route_id == route_id,
                RouteItem.stay_minutes.is_(None) | (RouteItem.stay_minutes > 0),
            )
            .group_by(RouteItem.slot_status)
        ).all()
    )
    counts = {status: count for status, count in rows}
    filled = counts.get(RouteItemSlotStatus.FILLED, 0)
    needs = counts.get(RouteItemSlotStatus.NEEDS_VERIFICATION, 0)
    unfilled = counts.get(RouteItemSlotStatus.UNFILLED, 0)
    meal_unfilled = (
        db.scalar(
            select(func.count())
            .select_from(RouteItem)
            .join(RouteDay, RouteDay.id == RouteItem.route_day_id)
            .where(
                RouteDay.route_id == route_id,
                RouteItem.slot_status == RouteItemSlotStatus.UNFILLED,
                RouteItem.item_type == ScheduleItemType.RESTAURANT,
            )
        )
        or 0
    )
    return {
        "slot_total": filled + needs + unfilled,
        "filled": filled,
        "needs_verification": needs,
        "unfilled": unfilled,
        "meal_unfilled": meal_unfilled,
        "travel_minutes": _travel_minutes(db, route_id),
    }


def _travel_minutes(db: Session, route_id: uuid.UUID) -> int:
    """route_moves 의 양끝 좌표로 이동시간을 추정해 합산한다(캐시 없이 추정)."""
    items = {
        item.id: item
        for item in db.scalars(
            select(RouteItem).join(RouteDay, RouteDay.id == RouteItem.route_day_id).where(
                RouteDay.route_id == route_id
            )
        )
    }
    total = 0.0
    for move in db.scalars(
        select(RouteMove).where(
            RouteMove.from_item_id.in_(list(items)), RouteMove.to_item_id.in_(list(items))
        )
    ):
        origin = _coord(items.get(move.from_item_id))
        dest = _coord(items.get(move.to_item_id))
        if origin is None or dest is None:
            continue
        try:
            total += estimate_leg(origin, dest, move.transport).duration_min
        except ValueError:
            continue
    return round(total)


def _coord(item: RouteItem | None) -> tuple[float, float] | None:
    if item is None or item.latitude is None or item.longitude is None:
        return None
    return float(item.latitude), float(item.longitude)


def _aggregate(results: list[dict]) -> dict:
    """권역·속도·박수별 실패율·충족률·확인필요율."""

    def rates(subset: list[dict]) -> dict:
        n = len(subset)
        failed = sum(1 for r in subset if r["status"] == "failed")
        slots = sum(r["slot_total"] for r in subset)
        filled = sum(r["filled"] for r in subset)
        needs = sum(r["needs_verification"] for r in subset)
        return {
            "scenarios": n,
            "failure_rate": round(failed / n, 3) if n else 0.0,
            "fill_rate": round(filled / slots, 3) if slots else 0.0,
            "needs_check_rate": round(needs / slots, 3) if slots else 0.0,
        }

    def group(key: str) -> dict:
        buckets: dict[object, list[dict]] = defaultdict(list)
        for r in results:
            buckets[r[key]].append(r)
        return {str(k): rates(v) for k, v in buckets.items()}

    return {
        "overall": rates(results),
        "by_region": group("region"),
        "by_pace": group("pace"),
        "by_nights": group("nights"),
    }


def _print_report(results: list[dict], summary: dict) -> None:
    print("\n=== 시나리오별 ===")
    header = (
        f"{'권역':<12}{'속도':<9}{'박':<4}{'상태':<11}{'슬롯':>5}{'채움':>5}"
        f"{'확인':>5}{'빈':>4}{'식사빈':>6}{'이동(분)':>8}{'ms':>8}"
    )
    print(header)
    for r in sorted(results, key=lambda x: (x["region"], x["pace"], x["nights"])):
        print(
            f"{r['region']:<12}{r['pace']:<9}{r['nights']:<4}{r['status']:<11}"
            f"{r['slot_total']:>5}{r['filled']:>5}{r['needs_verification']:>5}"
            f"{r['unfilled']:>4}{r['meal_unfilled']:>6}{r['travel_minutes']:>8}{r['elapsed_ms']:>8}"
        )

    def _table(title: str, block: dict) -> None:
        print(f"\n=== {title} ===")
        print(f"{'':<14}{'시나리오':>8}{'실패율':>8}{'충족률':>8}{'확인필요율':>10}")
        for key, rate in block.items():
            print(
                f"{key:<14}{rate['scenarios']:>8}{rate['failure_rate']:>8}"
                f"{rate['fill_rate']:>8}{rate['needs_check_rate']:>10}"
            )

    o = summary["overall"]
    print(
        f"\n=== 전체 === 시나리오 {o['scenarios']} · 실패율 {o['failure_rate']} · "
        f"충족률 {o['fill_rate']} · 확인필요율 {o['needs_check_rate']}"
    )
    _table("권역별", summary["by_region"])
    _table("속도별", summary["by_pace"])
    _table("박수별", summary["by_nights"])


def main() -> None:
    parser = argparse.ArgumentParser(description="시나리오 매트릭스 측정(오프라인)")
    parser.add_argument(
        "--database-url",
        default="postgresql+psycopg://omeong:omeong@localhost:5432/omeong_test",
        help="대상 DB(기본 로컬 omeong_test). 로컬 호스트만 허용(그 외 거부).",
    )
    parser.add_argument("--json", dest="json_path", default=None, help="결과 JSON 저장 경로")
    parser.add_argument("--pets", choices=["small", "none", "large"], default="small")
    args = parser.parse_args()

    _require_local(args.database_url)
    _install_offline_stubs()

    engine = create_engine(args.database_url, connect_args={"options": "-c timezone=Asia/Seoul"})
    place_count = 0
    connection = engine.connect()
    transaction = connection.begin()
    # generate_route 의 commit() 이 바깥 트랜잭션을 끝내지 않고 SAVEPOINT 만 풀게 한다.
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        place_count = db.scalar(select(func.count()).select_from(Place)) or 0
        user = User(
            id=uuid.uuid4(),
            nickname="측정",
            email=f"measure-{uuid.uuid4().hex}@local",
            password_hash="measure-only",
        )
        db.add(user)
        db.flush()

        results = [
            _run_scenario(db, user, region, pace, nights, args.pets)
            for region in REGIONS
            for pace in PACES
            for nights in NIGHTS
        ]
    finally:
        db.close()
        transaction.rollback()
        connection.close()
        engine.dispose()

    summary = _aggregate(results)
    print(f"대상 DB place 수: {place_count} (pets={args.pets})")
    if place_count == 0:
        print(
            "경고: 대상 DB 에 장소가 없습니다 — 모든 시나리오가 실패합니다. "
            "시드가 있는 DB 로 측정하세요."
        )
    _print_report(results, summary)

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "place_count": place_count,
                    "pets": args.pets,
                    "results": results,
                    "summary": summary,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\n→ {args.json_path}")


if __name__ == "__main__":
    main()
