"""카카오에서 가져온 장소를 검색에 노출시킨다.

2026-08-12 임포트가 카카오 장소를 ``is_active=false`` 로 넣고 켜지 않았다.
껐다는 기록이 없고 중복도 아니어서, 담당자 확인 후 켜기로 했다.
근거와 숫자는 ``docs/planning/chatbot-design-decisions.md`` 에 있다.

일회성 SQL 로 처리하면 나중에 "장소가 왜 601개 늘었지?" 를 아무도 못 쫓는다.
공유 DB 라 더 그렇다. 그래서 스크립트로 남긴다.

**8/15 에 수정된 카카오+kcisa 28건은 제외한다.** 생성 이후 누군가 건드린
흔적이 있어서, 의도적으로 꺼둔 것일 가능성을 배제할 수 없다.

    # 몇 건인지 보기만 (기본)
    cd apps/api && uv run python -m scripts.activate_kakao_places

    # 실제로 켜기
    cd apps/api && uv run python -m scripts.activate_kakao_places --apply

되돌리려면 ``--apply`` 가 남긴 id 파일을 ``--revert`` 로 넘긴다.

    cd apps/api && uv run python -m scripts.activate_kakao_places \
        --revert activated-20260828-153000.txt
"""

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Place, PlaceExternalRef
from app.db.session import SessionLocal

#: 이 출처로 들어온 장소를 켠다.
TARGET_PROVIDER = "kakao"

#: 이 출처가 함께 붙어 있으면 건너뛴다. 8/15 에 수정된 28건이 여기 해당한다.
SKIP_PROVIDER = "kcisa"


def _has_ref(provider: str):
    """장소에 그 출처의 외부 참조가 달려 있는지."""
    return (
        select(PlaceExternalRef.id)
        .where(
            PlaceExternalRef.place_id == Place.id,
            PlaceExternalRef.provider == provider,
        )
        .exists()
    )


def target_ids(db: Session) -> list[uuid.UUID]:
    """켤 장소 id. 이미 켜진 것은 빠지므로 몇 번 돌려도 안전하다."""
    statement = (
        select(Place.id)
        .where(
            Place.is_active.is_(False),
            _has_ref(TARGET_PROVIDER),
            ~_has_ref(SKIP_PROVIDER),
        )
        .order_by(Place.id)
    )
    return list(db.scalars(statement))


def summarize(db: Session, place_ids: list[uuid.UUID]) -> list[tuple[str, int]]:
    """카테고리별 건수. 무엇이 늘어나는지 눈으로 보라고 찍는다."""
    if not place_ids:
        return []
    statement = (
        select(Place.category, func.count())
        .where(Place.id.in_(place_ids))
        .group_by(Place.category)
        .order_by(func.count().desc())
    )
    return [(category, count) for category, count in db.execute(statement)]


def set_active(db: Session, place_ids: list[uuid.UUID], *, active: bool) -> int:
    """지정한 장소의 노출 여부를 바꾼다."""
    if not place_ids:
        return 0
    result = db.execute(
        update(Place).where(Place.id.in_(place_ids)).values(is_active=active)
    )
    return result.rowcount


def describe_target() -> str:
    """접속할 DB. 어디를 건드리는지 모르고 실행하는 사고를 막는다."""
    parsed = urlparse(settings.database_url)
    return f"{parsed.hostname or '?'}:{parsed.port or 5432}{parsed.path}"


def is_shared_db() -> bool:
    """로컬 컨테이너가 아니면 공유 DB 로 본다."""
    hostname = urlparse(settings.database_url).hostname or ""
    return hostname not in {"localhost", "127.0.0.1", "postgres", "db"}


def confirm(target: str, count: int) -> bool:
    """공유 DB 에는 한 번 더 묻는다. 팀원 앱 목록이 같이 바뀐다."""
    print()
    print(f"  ⚠ 공유 DB 입니다 — {target}")
    print(f"    {count}곳이 모든 팀원의 장소 목록에 나타납니다.")
    answer = input("    계속하려면 'yes' 를 입력하세요: ").strip()
    return answer == "yes"


def read_ids(path: Path) -> list[uuid.UUID]:
    lines = path.read_text().split()
    return [uuid.UUID(line) for line in lines if line]


def write_ids(place_ids: list[uuid.UUID]) -> Path:
    """켠 장소를 파일로 남긴다. 되돌릴 때 이 목록 그대로 쓴다."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(f"activated-{stamp}.txt")
    path.write_text("\n".join(str(place_id) for place_id in place_ids) + "\n")
    return path


def run_activate(db: Session, *, apply: bool) -> int:
    # 조회보다 먼저 찍는다. 접속이 막히면 여기서 멈추는데,
    # 아무것도 안 뜬 채로 기다리면 어디에 붙는 중인지조차 알 수 없다.
    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print("조회 중...", flush=True)

    place_ids = target_ids(db)
    print(f"켤 장소 : {len(place_ids)}곳")

    for category, count in summarize(db, place_ids):
        print(f"          {category:<20} {count:>5}")

    if not place_ids:
        print("\n켤 것이 없습니다. 이미 반영되어 있습니다.")
        return 0

    if not apply:
        print("\n확인만 했습니다. 실제로 켜려면 --apply 를 붙이세요.")
        return 0

    if is_shared_db() and not confirm(target, len(place_ids)):
        print("\n취소했습니다.")
        return 1

    changed = set_active(db, place_ids, active=True)
    db.commit()

    path = write_ids(place_ids)
    print(f"\n{changed}곳을 켰습니다.")
    print(f"되돌릴 때 쓸 목록 : {path}")
    return 0


def run_revert(db: Session, path: Path) -> int:
    if not path.exists():
        print(f"파일이 없습니다: {path}")
        return 1

    place_ids = read_ids(path)

    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print(f"끌 장소 : {len(place_ids)}곳  ({path})", flush=True)

    if is_shared_db() and not confirm(target, len(place_ids)):
        print("\n취소했습니다.")
        return 1

    changed = set_active(db, place_ids, active=False)
    db.commit()
    print(f"\n{changed}곳을 다시 껐습니다.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="실제로 켠다. 없으면 몇 건인지 보여주기만 한다.",
    )
    parser.add_argument(
        "--revert",
        type=Path,
        metavar="파일",
        help="--apply 가 남긴 id 파일을 받아 다시 끈다.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.revert:
            return run_revert(db, args.revert)
        return run_activate(db, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
