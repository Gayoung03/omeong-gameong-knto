"""environment 가 NULL 인 장소에 실내/실외/혼합(place_environment)을 채운다.

`environment` 는 날씨 적합도 점수(weather_score)와 실내외 추천에 쓰는데 810곳이
비어 있어 그 축이 중립(0.5)으로만 계산된다. 카테고리와 설명·정책으로 추정해 채운다.

규칙 (설명 키워드는 **attraction 에만** 적용):
1. beach/oreum/walking_trail → outdoor (설명 무시)
2. cafe/restaurant/restaurant_cafe/accommodation/pet_service/etc … → indoor (설명 무시)
3. attraction:
   a. 설명에 실내/박물관/전시/미술관/기념관/체험관 → indoor
   b. 설명에 해변/오름/숲/공원/정원/목장/해안 → outdoor
   c. 정책 outdoor_only → outdoor, 그 외(indoor_allowed·미확인 등) → mixed

카테고리로 실내/실외가 이미 확실한 곳(공원 옆 카페는 실내, 실내 전시관이 딸린 해변은
실외)에는 설명 키워드를 적용하지 않는다 — environment 는 비 오는 날 실내 우선 규칙에
쓰이므로 카테고리 신호를 뒤집으면 안 된다. 유형이 다양한 attraction 만 설명으로 좁힌다.

    cd apps/api && uv run python -m scripts.backfill_place_environment          # 조회만
    cd apps/api && uv run python -m scripts.backfill_place_environment --apply
    cd apps/api && uv run python -m scripts.backfill_place_environment \
        --revert environment-filled-20260908-120000.txt
"""

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import Place, PlacePetPolicy
from app.db.models.enums import PetPolicyType, PlaceEnvironment
from app.db.session import SessionLocal
from scripts.activate_kakao_places import confirm, describe_target, is_shared_db

INDOOR_DESC_KEYWORDS = ("실내", "박물관", "전시", "미술관", "기념관", "체험관")
OUTDOOR_DESC_KEYWORDS = ("해변", "오름", "숲", "공원", "정원", "목장", "해안")
OUTDOOR_CATEGORIES = {"beach", "oreum", "walking_trail"}


def classify(
    category: str, description: str | None, policy_type: PetPolicyType | None
) -> tuple[PlaceEnvironment, str]:
    """(환경, 적용 규칙 이름). 규칙 이름은 리포트 집계용이다.

    설명 키워드는 유형이 다양한 attraction 에만 적용한다 — 카테고리로 실내/실외가
    이미 확실한 곳은 뒤집지 않는다.
    """

    if category in OUTDOOR_CATEGORIES:
        return PlaceEnvironment.OUTDOOR, "category_outdoor"
    if category != "attraction":
        return PlaceEnvironment.INDOOR, "category_indoor"

    text = description or ""
    if any(keyword in text for keyword in INDOOR_DESC_KEYWORDS):
        return PlaceEnvironment.INDOOR, "attraction_desc_indoor"
    if any(keyword in text for keyword in OUTDOOR_DESC_KEYWORDS):
        return PlaceEnvironment.OUTDOOR, "attraction_desc_outdoor"
    if policy_type == PetPolicyType.OUTDOOR_ONLY:
        return PlaceEnvironment.OUTDOOR, "attraction_outdoor_only"
    return PlaceEnvironment.MIXED, "attraction_mixed"


def target_rows(db: Session) -> list[tuple[uuid.UUID, str, str | None]]:
    """environment 가 비어 있는 장소의 (id, category, description).

    전체 Place ORM 이 아니라 필요한 컬럼만 읽어, 아직 마이그레이션 안 된 컬럼이 있어도
    조회가 돌아가게 한다.
    """
    return list(
        db.execute(
            select(Place.id, Place.category, Place.description)
            .where(Place.environment.is_(None))
            .order_by(Place.id)
        ).all()
    )


def policy_types(db: Session, place_ids: list[uuid.UUID]) -> dict[uuid.UUID, PetPolicyType]:
    """장소별 최신 정책 유형(attraction 판정용)."""
    if not place_ids:
        return {}
    rows = db.scalars(
        select(PlacePetPolicy)
        .where(PlacePetPolicy.place_id.in_(place_ids))
        .order_by(PlacePetPolicy.place_id, PlacePetPolicy.verified_at.desc().nullslast())
    ).all()
    result: dict[uuid.UUID, PetPolicyType] = {}
    for row in rows:
        result.setdefault(row.place_id, row.policy_type)
    return result


def plan(
    rows: list[tuple[uuid.UUID, str, str | None]], policies: dict[uuid.UUID, PetPolicyType]
) -> list[tuple[uuid.UUID, PlaceEnvironment, str]]:
    """(장소 id, 채울 환경, 적용 규칙)."""
    return [
        (place_id, *classify(category, description, policies.get(place_id)))
        for place_id, category, description in rows
    ]


def summarize(
    filled: list[tuple[uuid.UUID, PlaceEnvironment, str]],
) -> list[tuple[str, str, int]]:
    """(규칙, 환경, 건수) 내림차순."""
    counts: dict[tuple[str, str], int] = {}
    for _, environment, rule in filled:
        key = (rule, environment.value)
        counts[key] = counts.get(key, 0) + 1
    return sorted(
        ((rule, env, count) for (rule, env), count in counts.items()),
        key=lambda row: row[2],
        reverse=True,
    )


def apply_fills(db: Session, filled: list[tuple[uuid.UUID, PlaceEnvironment, str]]) -> int:
    by_environment: dict[PlaceEnvironment, list[uuid.UUID]] = {}
    for place_id, environment, _ in filled:
        by_environment.setdefault(environment, []).append(place_id)
    changed = 0
    for environment, place_ids in by_environment.items():
        result = db.execute(
            update(Place)
            .where(Place.id.in_(place_ids), Place.environment.is_(None))
            .values(environment=environment)
        )
        changed += result.rowcount
    return changed


def write_ids(place_ids: list[uuid.UUID]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(f"environment-filled-{stamp}.txt")
    path.write_text("".join(f"{place_id}\n" for place_id in place_ids), encoding="utf-8")
    return path


def read_ids(path: Path) -> list[uuid.UUID]:
    return [
        uuid.UUID(line.strip())
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_fill(db: Session, *, apply: bool) -> int:
    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print("조회 중...", flush=True)

    rows = target_rows(db)
    policies = policy_types(db, [row[0] for row in rows])
    filled = plan(rows, policies)

    print(f"환경을 채울 장소 : {len(filled)}곳 (environment IS NULL)")
    for rule, environment, count in summarize(filled):
        print(f"            {rule:<24} → {environment:<8} {count:>5}")

    if not filled:
        print("\n채울 것이 없습니다. 이미 반영되어 있습니다.")
        return 0
    if not apply:
        print("\n확인만 했습니다. 실제로 채우려면 --apply 를 붙이세요.")
        return 0
    if is_shared_db() and not confirm(target, len(filled)):
        print("\n취소했습니다.")
        return 1

    path = write_ids([place_id for place_id, _, _ in filled])
    changed = apply_fills(db, filled)
    db.commit()
    print(f"\n{changed}곳의 environment 를 채웠습니다.")
    print(f"되돌릴 때 쓸 목록 : {path}")
    return 0


def run_revert(db: Session, path: Path) -> int:
    if not path.exists():
        print(f"파일이 없습니다: {path}")
        return 1
    ids = read_ids(path)
    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print(f"되돌릴 장소 : {len(ids)}곳 ({path})", flush=True)
    if is_shared_db() and not confirm(target, len(ids)):
        print("\n취소했습니다.")
        return 1
    result = db.execute(update(Place).where(Place.id.in_(ids)).values(environment=None))
    db.commit()
    print(f"\n{result.rowcount}곳의 environment 를 NULL 로 되돌렸습니다.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="실제로 채운다. 없으면 조회만.")
    parser.add_argument(
        "--revert", type=Path, metavar="파일", help="--apply 가 남긴 파일을 NULL 로 되돌린다."
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.revert:
            return run_revert(db, args.revert)
        return run_fill(db, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
