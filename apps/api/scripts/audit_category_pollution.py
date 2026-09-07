"""자연·해변 카테고리에 섞인 숙소·카페를 이름으로 찾아 정정 후보를 낸다.

`beach`·`oreum`·`walking_trail` 은 관광 후보로 쓰이는데, 이름에 펜션·스테이·하우스·
게스트·리조트·숙소·카페가 들어간 행이 섞이면(예: "…해변펜션"이 beach 로) 추천 다양성과
동선이 망가진다. repair_place_data 의 CategoryCorrection 선례처럼 **정정 후보만** 뽑아
리포트한다. 실제 반영(apply)은 사람이 후보를 검수한 뒤 repair_place_data 에 확정
항목으로 옮겨 처리한다 — 이 스크립트는 DB 를 바꾸지 않는다.

    cd apps/api && uv run python -m scripts.audit_category_pollution
    cd apps/api && uv run python -m scripts.audit_category_pollution --json
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Place
from app.db.session import SessionLocal
from scripts.activate_kakao_places import describe_target

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
    places = db.scalars(
        select(Place)
        .where(Place.category.in_(SCANNED_CATEGORIES))
        .order_by(Place.category, Place.name)
    ).all()
    candidates: list[CategoryCandidate] = []
    for place in places:
        match = proposed_target(place.name)
        if match is None:
            continue
        target, keyword = match
        if target == place.category:
            continue
        candidates.append(
            CategoryCandidate(
                place_id=str(place.id),
                name=place.name,
                from_category=place.category,
                to_category=target,
                matched_keyword=keyword,
            )
        )
    return candidates


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


def run(db: Session, *, write: bool) -> int:
    print(f"대상 DB : {describe_target()}", flush=True)
    print("조회 중...", flush=True)

    totals = category_totals(db)
    candidates = scan(db)

    print("\n점검 카테고리 (전체 건수)")
    for category in SCANNED_CATEGORIES:
        print(f"  {category:<16} {totals.get(category, 0):>5}")

    print(f"\n정정 후보 : {len(candidates)}곳 (이름에 숙소·카페 키워드)")
    for candidate in candidates:
        print(
            f"  [{candidate.matched_keyword}] {candidate.name[:24]:<24} "
            f"{candidate.from_category} → {candidate.to_category}  {candidate.place_id}"
        )

    if not candidates:
        print("  (없음)")
    else:
        print(
            "\n검수 후 repair_place_data 의 CATEGORY_CORRECTIONS 에 확정 항목으로 옮겨 "
            "반영하세요. 이 스크립트는 DB 를 바꾸지 않습니다."
        )
    if write and candidates:
        print(f"\n후보 목록 파일 : {write_json(candidates)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="후보를 JSON 파일로도 저장한다.")
    args = parser.parse_args()

    with SessionLocal() as db:
        return run(db, write=args.json)


if __name__ == "__main__":
    sys.exit(main())
