"""주소가 서귀포인데 권역이 제주시로 되어 있는 장소를 옮긴다.

`region` 은 챗봇 검색과 장소 목록 API 가 **SQL 의 WHERE 조건으로** 쓰는 값이다.
값이 틀리면 그 장소는 검색에 도달조차 하지 못한다 — 사용자에게는 "서귀포에
갈 곳이 없다" 로 보인다. 근거와 숫자는
``docs/planning/chatbot-design-decisions.md`` 4장에 있다.

**주소는 처음부터 맞았고 권역만 틀리게 붙었다.** 그래서 고칠 근거가 데이터
안에 이미 있다 — 사람이 하나씩 찾아볼 필요가 없다.

오류는 **한 방향으로만** 난다. 주소에 "제주시"가 들어간 장소가 서귀포 권역에
들어간 경우는 없다. 그래서 반대 방향은 건드리지 않는다.

일회성 SQL 로 처리하면 나중에 "장소 110개가 왜 옮겨졌지?" 를 아무도 못 쫓는다.
공유 DB 라 더 그렇다. `activate_kakao_places.py` 선례대로 스크립트로 남긴다.

    # 몇 건인지 보기만 (기본, 조회만 하므로 공유 DB 에도 안전하다)
    cd apps/api && uv run python -m scripts.fix_place_regions

    # 실제로 옮기기
    cd apps/api && uv run python -m scripts.fix_place_regions --apply

되돌리려면 ``--apply`` 가 남긴 파일을 ``--revert`` 로 넘긴다. 파일에는
**장소 id 와 옮기기 전 권역**이 함께 들어 있어 원래 값으로 정확히 돌아간다.

    cd apps/api && uv run python -m scripts.fix_place_regions \
        --revert region-fixed-20260829-234500.txt
"""

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Place
from app.db.session import SessionLocal

#: 주소에 이 말이 들어가면 서귀포시 소속이다.
ADDRESS_KEYWORD = "서귀포"

#: 주소에 이것이 **함께** 들어 있으면 잘못 고른 것일 수 있다.
#: 제주시에 있는데 도로명에 "서귀포"가 들어가는 경우 등. 실행 전에 경고한다.
CONFLICT_KEYWORD = "제주시"

#: 서귀포시에 속하는 권역. 여기 들어 있으면 이미 맞은 것이라 건드리지 않는다.
#: 표선면·성산읍·중문동 모두 행정구역상 서귀포시다.
SEOGWIPO_REGIONS = ("서귀포시/모슬포", "표선/성산", "중문")

#: 애매할 때 보낼 곳. 서귀포 계열 중 가장 넓다.
DEFAULT_REGION = "서귀포시/모슬포"

#: 주소에 이 말이 있으면 그 권역으로. **판단이 아니라 행정구역 사실만** 넣는다.
#: 남원읍처럼 어느 권역에 넣을지 논의가 필요한 것은 여기 넣지 않고
#: `DEFAULT_REGION` 으로 보낸다(2단계에서 정밀 배분).
ADDRESS_TO_REGION: tuple[tuple[str, str], ...] = (
    ("중문동", "중문"),
    ("표선면", "표선/성산"),
    ("성산읍", "표선/성산"),
)


def _address_of(place: Place) -> str:
    """지번 주소를 우선 보고, 없으면 도로명 주소를 본다."""
    return place.address or place.road_address or ""


def _target_region(address: str) -> str:
    for keyword, region in ADDRESS_TO_REGION:
        if keyword in address:
            return region
    return DEFAULT_REGION


def target_places(db: Session) -> list[Place]:
    """옮길 장소. 이미 서귀포 계열이면 빠지므로 몇 번 돌려도 안전하다."""
    statement = (
        select(Place)
        .where(
            or_(
                Place.address.contains(ADDRESS_KEYWORD),
                Place.road_address.contains(ADDRESS_KEYWORD),
            ),
            or_(
                Place.region.is_(None),
                Place.region.notin_(SEOGWIPO_REGIONS),
            ),
        )
        .order_by(Place.id)
    )
    return list(db.scalars(statement))


def plan(places: list[Place]) -> list[tuple[uuid.UUID, str, str]]:
    """(장소 id, 지금 권역, 옮길 권역). 옮길 필요가 없으면 뺀다."""
    moves = []
    for place in places:
        after = _target_region(_address_of(place))
        before = place.region or ""
        if before != after:
            moves.append((place.id, before, after))
    return moves


def summarize(moves: list[tuple[uuid.UUID, str, str]]) -> list[tuple[str, str, int]]:
    """어디서 어디로 몇 건이 가는지. 눈으로 보고 판단하라고 찍는다."""
    counts: dict[tuple[str, str], int] = {}
    for _, before, after in moves:
        counts[(before, after)] = counts.get((before, after), 0) + 1
    return sorted(
        ((before, after, count) for (before, after), count in counts.items()),
        key=lambda row: row[2],
        reverse=True,
    )


def count_active(db: Session, place_ids: list[uuid.UUID]) -> int:
    """그중 검색에 노출 중인 것. 사용자가 실제로 체감하는 숫자다."""
    if not place_ids:
        return 0
    return db.scalar(
        select(func.count())
        .select_from(Place)
        .where(Place.id.in_(place_ids), Place.is_active.is_(True))
    ) or 0


def set_regions(db: Session, moves: list[tuple[uuid.UUID, str, str]]) -> int:
    """옮길 권역이 같은 것끼리 묶어 UPDATE 한다."""
    by_region: dict[str, list[uuid.UUID]] = {}
    for place_id, _, after in moves:
        by_region.setdefault(after, []).append(place_id)

    changed = 0
    for region, place_ids in by_region.items():
        result = db.execute(
            update(Place).where(Place.id.in_(place_ids)).values(region=region)
        )
        changed += result.rowcount
    return changed


def describe_target() -> str:
    """접속할 DB. 어디를 건드리는지 모르고 실행하는 사고를 막는다."""
    parsed = urlparse(settings.database_url)
    return f"{parsed.hostname or '?'}:{parsed.port or 5432}{parsed.path}"


def is_shared_db() -> bool:
    """로컬 컨테이너가 아니면 공유 DB 로 본다."""
    hostname = urlparse(settings.database_url).hostname or ""
    return hostname not in {"localhost", "127.0.0.1", "postgres", "db"}


def confirm(target: str, count: int, active: int) -> bool:
    """공유 DB 에는 한 번 더 묻는다. 팀원 앱의 지역 필터도 같이 바뀐다."""
    print()
    print(f"  ⚠ 공유 DB 입니다 — {target}")
    print(f"    장소 {count}곳의 지역이 바뀝니다(검색 노출 중 {active}곳).")
    print("    팀원 앱의 지역 필터 결과도 함께 바뀝니다.")
    answer = input("    계속하려면 'yes' 를 입력하세요: ").strip()
    return answer == "yes"


def read_moves(path: Path) -> list[tuple[uuid.UUID, str]]:
    """되돌릴 목록. `<id>\\t<옮기기 전 권역>` 한 줄에 하나씩."""
    moves = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        place_id, _, before = line.partition("\t")
        moves.append((uuid.UUID(place_id.strip()), before.strip()))
    return moves


def write_moves(moves: list[tuple[uuid.UUID, str, str]]) -> Path:
    """옮긴 장소를 파일로 남긴다.

    **id 만 남기면 안 된다.** 되돌릴 때 원래 권역이 무엇이었는지 알 수 없어
    전부 한 값으로 밀어버리게 된다. 옮기기 전 권역을 함께 적는다.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(f"region-fixed-{stamp}.txt")
    path.write_text(
        "".join(f"{place_id}\t{before}\n" for place_id, before, _ in moves),
        encoding="utf-8",
    )
    return path


def preview(db: Session, places: list[Place], moves: list[tuple[uuid.UUID, str, str]]) -> None:
    """앞의 몇 건을 주소와 함께 보여준다. 숫자만으로는 맞는지 알 수 없다."""
    by_id = {place.id: place for place in places}
    print("\n  예시 (앞 10건)")
    for place_id, before, after in moves[:10]:
        place = by_id[place_id]
        address = _address_of(place)
        if len(address) > 34:
            address = address[:33] + "…"
        print(f"    {place.name[:16]:<16} {address:<35} {before} → {after}")


def conflicts(places: list[Place], moves: list[tuple[uuid.UUID, str, str]]) -> list[Place]:
    """주소에 "서귀포"와 "제주시"가 **함께** 있는 것.

    이걸 안 보고 넘기면 제주시 장소를 서귀포로 보내게 된다. 반대 방향 오류를
    우리 손으로 만드는 셈이라, 한 건이라도 있으면 멈추고 눈으로 본다.
    """
    moving = {place_id for place_id, _, _ in moves}
    return [
        place
        for place in places
        if place.id in moving and CONFLICT_KEYWORD in _address_of(place)
    ]


def run_fix(db: Session, *, apply: bool) -> int:
    # 조회보다 먼저 찍는다. 접속이 막히면 여기서 멈추는데,
    # 아무것도 안 뜬 채로 기다리면 어디에 붙는 중인지조차 알 수 없다.
    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print("조회 중...", flush=True)

    places = target_places(db)
    moves = plan(places)
    place_ids = [place_id for place_id, _, _ in moves]
    active = count_active(db, place_ids)

    print(f"옮길 장소 : {len(moves)}곳  (검색 노출 중 {active}곳)")
    for before, after, count in summarize(moves):
        print(f"            {before:<18} → {after:<12} {count:>5}")

    if not moves:
        print("\n옮길 것이 없습니다. 이미 반영되어 있습니다.")
        return 0

    preview(db, places, moves)

    suspect = conflicts(places, moves)
    if suspect:
        print(f"\n  ⚠ 주소에 '{CONFLICT_KEYWORD}' 가 함께 들어간 장소 {len(suspect)}곳")
        print("    잘못 고른 것일 수 있습니다. 확인하고 진행하세요.")
        for place in suspect[:10]:
            print(f"      {place.name[:16]:<16} {_address_of(place)}")
    else:
        print(f"\n  ✓ 주소에 '{CONFLICT_KEYWORD}' 가 함께 든 장소는 없습니다.")

    if not apply:
        print("\n확인만 했습니다. 실제로 옮기려면 --apply 를 붙이세요.")
        return 0

    if is_shared_db() and not confirm(target, len(moves), active):
        print("\n취소했습니다.")
        return 1

    path = write_moves(moves)  # 바꾸기 전에 먼저 남긴다
    changed = set_regions(db, moves)
    db.commit()

    print(f"\n{changed}곳의 지역을 바꿨습니다.")
    print(f"되돌릴 때 쓸 목록 : {path}")
    print("\n장소 질문 답변을 다시 확인해 주세요. 검색 결과가 바뀝니다.")
    return 0


def run_revert(db: Session, path: Path) -> int:
    if not path.exists():
        print(f"파일이 없습니다: {path}")
        return 1

    saved = read_moves(path)

    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print(f"되돌릴 장소 : {len(saved)}곳  ({path})", flush=True)

    active = count_active(db, [place_id for place_id, _ in saved])
    if is_shared_db() and not confirm(target, len(saved), active):
        print("\n취소했습니다.")
        return 1

    by_region: dict[str, list[uuid.UUID]] = {}
    for place_id, before in saved:
        by_region.setdefault(before, []).append(place_id)

    changed = 0
    for region, place_ids in by_region.items():
        result = db.execute(
            update(Place).where(Place.id.in_(place_ids)).values(region=region)
        )
        changed += result.rowcount
    db.commit()

    print(f"\n{changed}곳을 원래 지역으로 돌렸습니다.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제로 옮긴다. 없으면 몇 건인지 보여주기만 한다.",
    )
    parser.add_argument(
        "--revert",
        type=Path,
        metavar="파일",
        help="--apply 가 남긴 파일을 받아 원래 지역으로 돌린다.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.revert:
            return run_revert(db, args.revert)
        return run_fix(db, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
