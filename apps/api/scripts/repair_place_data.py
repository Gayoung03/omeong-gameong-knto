"""카카오 장소 활성화 누락과 확인된 숙소 카테고리 오분류를 정정한다.

기본 실행은 변경 대상을 출력만 한다. 실제 반영은 ``--apply`` 가 필요하다.
이미 정정된 행은 대상에서 빠지므로 여러 번 실행해도 안전하다.

    cd apps/api && uv run python -m scripts.repair_place_data
    cd apps/api && uv run python -m scripts.repair_place_data --apply

공유 DB에서는 적용 전에 ``yes`` 확인을 한 번 더 요구한다.
"""

import argparse
import sys
import uuid
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import Place
from app.db.session import SessionLocal
from scripts.activate_kakao_places import (
    confirm,
    describe_target,
    is_shared_db,
    set_active,
    summarize,
    target_ids,
    write_ids,
)


@dataclass(frozen=True)
class CategoryCorrection:
    place_id: uuid.UUID
    name: str
    from_category: str
    to_category: str


CATEGORY_CORRECTIONS = (
    CategoryCorrection(
        uuid.UUID("c40791d3-3d16-54a6-a80d-ecf64fd3eb4f"),
        "마레카펜션",
        "beach",
        "accommodation",
    ),
    CategoryCorrection(
        uuid.UUID("8381fd20-94d0-5334-b9b8-b26385240d95"),
        "아뜨네통나무펜션",
        "beach",
        "accommodation",
    ),
    CategoryCorrection(
        uuid.UUID("44727d8a-7517-58e0-ad9f-5693e803cc45"),
        "초원게스트하우스",
        "beach",
        "accommodation",
    ),
    CategoryCorrection(
        uuid.UUID("a8890469-c941-55a5-9c16-b4bb27e139c3"),
        "서귀포늘바다애견동반펜션",
        "beach",
        "accommodation",
    ),
)


def pending_category_corrections(db: Session) -> list[CategoryCorrection]:
    """아직 원래의 잘못된 카테고리로 남아 있는 장소만 반환한다."""

    places = {
        place.id: place
        for place in db.scalars(
            select(Place).where(
                Place.id.in_([correction.place_id for correction in CATEGORY_CORRECTIONS])
            )
        )
    }
    pending: list[CategoryCorrection] = []
    for correction in CATEGORY_CORRECTIONS:
        place = places.get(correction.place_id)
        if place is None:
            continue
        if place.name != correction.name:
            raise RuntimeError(
                f"장소 ID의 이름이 예상과 다릅니다: {correction.place_id} "
                f"({place.name!r} != {correction.name!r})"
            )
        if place.category == correction.from_category:
            pending.append(correction)
        elif place.category != correction.to_category:
            raise RuntimeError(
                f"장소 카테고리가 예상과 다릅니다: {correction.name} ({place.category})"
            )
    return pending


def apply_category_corrections(
    db: Session, corrections: list[CategoryCorrection]
) -> int:
    changed = 0
    for correction in corrections:
        result = db.execute(
            update(Place)
            .where(
                Place.id == correction.place_id,
                Place.name == correction.name,
                Place.category == correction.from_category,
            )
            .values(category=correction.to_category)
        )
        changed += result.rowcount
    return changed


def run(db: Session, *, apply: bool) -> int:
    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print("조회 중...", flush=True)

    activation_ids = target_ids(db)
    corrections = pending_category_corrections(db)
    print(f"활성화할 카카오 장소 : {len(activation_ids)}곳")
    for category, count in summarize(db, activation_ids):
        print(f"                      {category:<20} {count:>5}")
    print(f"카테고리를 고칠 숙소 : {len(corrections)}곳")
    for correction in corrections:
        print(
            f"                      {correction.name} "
            f"({correction.from_category} → {correction.to_category})"
        )

    total = len(activation_ids) + len(corrections)
    if total == 0:
        print("\n고칠 것이 없습니다. 이미 반영되어 있습니다.")
        return 0
    if not apply:
        print("\n확인만 했습니다. 실제로 고치려면 --apply 를 붙이세요.")
        return 0
    if is_shared_db() and not confirm(target, total):
        print("\n취소했습니다.")
        return 1

    activated = set_active(db, activation_ids, active=True)
    corrected = apply_category_corrections(db, corrections)
    db.commit()
    print(f"\n카카오 장소 {activated}곳을 활성화했습니다.")
    if activation_ids:
        print(f"활성화 되돌리기 목록 : {write_ids(activation_ids)}")
    print(f"숙소 카테고리 {corrected}곳을 정정했습니다.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="확인한 데이터 정정을 실제로 반영한다.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        return run(db, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
