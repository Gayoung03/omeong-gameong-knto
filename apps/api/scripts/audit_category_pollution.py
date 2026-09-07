"""자연·해변 카테고리에 섞인 숙소·카페를 찾아 리포트하고, 검수 확정분을 정정한다.

`beach`·`oreum`·`walking_trail` 은 관광 후보로 쓰이는데, 이름에 펜션·스테이·하우스·
게스트·리조트·숙소·카페가 들어간 행이 섞이면(예: "…해변펜션"이 beach 로) 추천 다양성과
동선이 망가진다.

두 가지를 한다:
1. **이름 규칙 스캔** — 후보를 리포트만 한다(사람 검수용, DB 미변경).
2. **검수 확정 정정** — 카카오 로컬·KCISA 로 확인한 CONFIRMED_CORRECTIONS 를
   repair_place_data 의 CategoryCorrection 패턴으로 적용한다(`--apply`).

    cd apps/api && uv run python -m scripts.audit_category_pollution           # 스캔·확정 조회
    cd apps/api && uv run python -m scripts.audit_category_pollution --apply   # 확정분 정정
    cd apps/api && uv run python -m scripts.audit_category_pollution \
        --revert category-fixed-20260908-120000.txt
"""

import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import Place
from app.db.session import SessionLocal
from scripts.activate_kakao_places import confirm, describe_target, is_shared_db
from scripts.repair_place_data import CategoryCorrection, apply_category_corrections

#: 점검 대상 — 자연/해변 계열. 이 카테고리에 숙소·카페 이름이 섞이면 오분류다.
SCANNED_CATEGORIES = ("beach", "oreum", "walking_trail")

#: 이름 키워드 → 올바른 카테고리. 앞에서부터 먼저 맞는 것을 쓴다(숙소 계열 우선).
KEYWORD_TARGETS: tuple[tuple[str, str], ...] = (
    ("펜션", "accommodation"),
    ("스테이", "accommodation"),
    ("하우스", "accommodation"),
    ("게스트", "accommodation"),
    ("리조트", "accommodation"),
    ("숙소", "accommodation"),
    ("카페", "cafe"),
)

#: 카카오 로컬·KCISA 로 검수 확정한 정정 (이름, 올바른 카테고리).
#: - 성산풀하우스: 카카오 여행>숙박>펜션 / 이리로스테이: 이름 규칙
#: - 바다스케치: 카카오 여행>숙박>콘도,리조트 / 제주에코스위츠: KCISA 반려동반여행>펜션
#: - 심바카레: 카카오 음식점>퓨전요리>퓨전일식
CONFIRMED_CORRECTIONS: tuple[tuple[str, str], ...] = (
    ("성산풀하우스", "accommodation"),
    ("이리로스테이", "accommodation"),
    ("바다스케치", "accommodation"),
    ("제주에코스위츠", "accommodation"),
    ("심바카레", "restaurant"),
)


@dataclass(frozen=True)
class CategoryCandidate:
    place_id: str
    name: str
    from_category: str
    to_category: str
    matched_keyword: str


def proposed_target(name: str) -> tuple[str, str] | None:
    """(맞는 카테고리, 매칭된 키워드). 해당 없으면 None."""
    for keyword, target in KEYWORD_TARGETS:
        if keyword in name:
            return target, keyword
    return None


def scan(db: Session) -> list[CategoryCandidate]:
    rows = db.execute(
        select(Place.id, Place.name, Place.category)
        .where(Place.category.in_(SCANNED_CATEGORIES))
        .order_by(Place.category, Place.name)
    ).all()
    candidates: list[CategoryCandidate] = []
    for place_id, name, category in rows:
        match = proposed_target(name)
        if match is None:
            continue
        target, keyword = match
        if target == category:
            continue
        candidates.append(CategoryCandidate(str(place_id), name, category, target, keyword))
    return candidates


def resolve_confirmed(db: Session) -> tuple[list[CategoryCorrection], list[str]]:
    """확정 정정을 이름으로 찾아 CategoryCorrection 으로. (정정목록, 건너뜀사유)."""
    names = [name for name, _ in CONFIRMED_CORRECTIONS]
    rows = db.execute(
        select(Place.id, Place.name, Place.category).where(Place.name.in_(names))
    ).all()
    by_name = {name: (place_id, category) for place_id, name, category in rows}
    corrections: list[CategoryCorrection] = []
    issues: list[str] = []
    for name, target in CONFIRMED_CORRECTIONS:
        entry = by_name.get(name)
        if entry is None:
            issues.append(f"미발견: {name}")
            continue
        place_id, category = entry
        if category == target:
            issues.append(f"이미 {target}: {name}")
            continue
        corrections.append(CategoryCorrection(place_id, name, category, target))
    return corrections, issues


def category_totals(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Place.category, func.count())
        .where(Place.category.in_(SCANNED_CATEGORIES))
        .group_by(Place.category)
    ).all()
    return {category: count for category, count in rows}


def write_json(candidates: list[CategoryCandidate]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(f"category-correction-candidates-{stamp}.json")
    path.write_text(
        json.dumps([asdict(candidate) for candidate in candidates], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def write_moves(corrections: list[CategoryCorrection]) -> Path:
    """되돌릴 목록: `<id>\\t<정정 전 카테고리>` 한 줄에 하나씩."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(f"category-fixed-{stamp}.txt")
    path.write_text(
        "".join(f"{c.place_id}\t{c.from_category}\n" for c in corrections), encoding="utf-8"
    )
    return path


def read_moves(path: Path) -> list[tuple[uuid.UUID, str]]:
    moves: list[tuple[uuid.UUID, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        place_id, _, before = line.partition("\t")
        moves.append((uuid.UUID(place_id.strip()), before.strip()))
    return moves


def run(db: Session, *, apply: bool, write: bool) -> int:
    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print("조회 중...", flush=True)

    totals = category_totals(db)
    candidates = scan(db)
    corrections, issues = resolve_confirmed(db)

    print("\n점검 카테고리 (전체 건수)")
    for category in SCANNED_CATEGORIES:
        print(f"  {category:<16} {totals.get(category, 0):>5}")

    print(f"\n이름 규칙 스캔 후보 : {len(candidates)}곳 (검수 대상, DB 미변경)")
    for candidate in candidates:
        print(
            f"  [{candidate.matched_keyword}] {candidate.name[:24]:<24} "
            f"{candidate.from_category} → {candidate.to_category}  {candidate.place_id}"
        )
    if write and candidates:
        print(f"  후보 목록 파일 : {write_json(candidates)}")

    print(f"\n검수 확정 정정 : {len(corrections)}건 (--apply 대상)")
    for correction in corrections:
        print(
            f"  {correction.name[:24]:<24} "
            f"{correction.from_category} → {correction.to_category}  {correction.place_id}"
        )
    for issue in issues:
        print(f"  (건너뜀) {issue}")

    if not corrections:
        print("\n적용할 확정 정정이 없습니다.")
        return 0
    if not apply:
        print("\n확인만 했습니다. 확정분을 반영하려면 --apply 를 붙이세요.")
        return 0
    if is_shared_db() and not confirm(target, len(corrections)):
        print("\n취소했습니다.")
        return 1

    path = write_moves(corrections)
    changed = apply_category_corrections(db, corrections)
    db.commit()
    print(f"\n{changed}건을 정정했습니다.")
    print(f"되돌릴 때 쓸 목록 : {path}")
    return 0


def run_revert(db: Session, path: Path) -> int:
    if not path.exists():
        print(f"파일이 없습니다: {path}")
        return 1
    moves = read_moves(path)
    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print(f"되돌릴 정정 : {len(moves)}건 ({path})", flush=True)
    if is_shared_db() and not confirm(target, len(moves)):
        print("\n취소했습니다.")
        return 1
    by_category: dict[str, list[uuid.UUID]] = {}
    for place_id, before in moves:
        by_category.setdefault(before, []).append(place_id)
    changed = 0
    for category, place_ids in by_category.items():
        result = db.execute(
            update(Place).where(Place.id.in_(place_ids)).values(category=category)
        )
        changed += result.rowcount
    db.commit()
    print(f"\n{changed}건을 원래 카테고리로 되돌렸습니다.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="검수 확정 정정을 실제로 반영한다.")
    parser.add_argument(
        "--revert", type=Path, metavar="파일", help="--apply 가 남긴 파일로 되돌린다."
    )
    parser.add_argument("--json", action="store_true", help="스캔 후보를 JSON 으로도 저장한다.")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.revert:
            return run_revert(db, args.revert)
        return run(db, apply=args.apply, write=args.json)


if __name__ == "__main__":
    sys.exit(main())
