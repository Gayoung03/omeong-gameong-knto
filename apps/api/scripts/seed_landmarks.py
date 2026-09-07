"""큐레이션한 명소를 places 에 내부 데이터(source='internal')로 적재한다.

추천 후보가 되는 관광·해변·오름·산책로 명소를 팀이 손으로 검수한 JSON 에서 넣는다.
입력은 ``scripts/data/landmarks/landmarks.json`` (배열). 항목 스키마는 이 저장소의
Phase 2 위임 문서를 따른다.

- **멱등**: 같은 이름이 있거나, 좌표 100m 이내 활성 장소가 있으면 건너뛰고 리포트한다.
- **검증 실패 시 전체 거부**: 하나라도 pet_policy.source_url 없음 / policy_type 어휘 밖 /
  tags 가 place_tags.code 밖 / region 불일치면, 이유를 출력하고 **아무것도 넣지 않는다.**
- 좌표가 없으면 카카오 지오코딩으로 채운다(주소·장소명 유도 좌표는 저장 허용).
- 정책은 source='internal', reliability_score=90. 태그는 source='internal', confidence=1.0.
  places.description_source='internal', created_by_user_id NULL, is_active true.

    cd apps/api && uv run python -m scripts.seed_landmarks              # 조회·검증만
    cd apps/api && uv run python -m scripts.seed_landmarks --apply
    cd apps/api && uv run python -m scripts.seed_landmarks --revert landmarks-seeded-….txt
"""

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Place, PlacePetPolicy, PlaceTag, PlaceTagLink
from app.db.models.enums import DataProvider, PetPolicyType, PlaceEnvironment
from app.db.session import SessionLocal
from app.integrations.maps.kakao import GeocodedAddress, geocode_address
from app.recommend.common.geo import haversine_m
from app.recommend.config.stay import default_stay_minutes
from scripts.activate_kakao_places import confirm, describe_target, is_shared_db

KST = ZoneInfo("Asia/Seoul")
Coordinate = tuple[float, float]

DATA_DEFAULT = "scripts/data/landmarks/landmarks.json"
ALLOWED_CATEGORIES = frozenset({"attraction", "beach", "oreum", "walking_trail"})
# places.region 의 기존 값. 이 밖의 값은 지역 필터에서 도달 불가라 거부한다.
REGIONS = frozenset(
    {
        "제주시/제주국제공항",
        "서귀포시/모슬포",
        "애월/한림/협재",
        "함덕/김녕/세화",
        "표선/성산",
        "중문",
    }
)
DUPLICATE_RADIUS_M = 100.0
POLICY_RELIABILITY = 90


@dataclass(frozen=True)
class ExistingPlace:
    name: str
    coord: Coordinate
    is_active: bool


@dataclass(frozen=True)
class ValidationError:
    name: str
    reason: str


def validate(items: list[dict], valid_tag_codes: frozenset[str]) -> list[ValidationError]:
    """부분 적재를 막기 위해 모든 항목을 먼저 검증한다."""

    policy_values = {policy.value for policy in PetPolicyType}
    errors: list[ValidationError] = []
    for item in items:
        name = str(item.get("name") or "?")
        if not item.get("name"):
            errors.append(ValidationError(name, "name 이 비어 있습니다"))
        category = item.get("category")
        if category not in ALLOWED_CATEGORIES:
            errors.append(ValidationError(name, f"category 가 허용 밖입니다: {category}"))
        region = item.get("region")
        if region not in REGIONS:
            errors.append(ValidationError(name, f"region 이 DB 기존 값 밖입니다: {region}"))
        unknown_tags = set(item.get("tags") or []) - valid_tag_codes
        if unknown_tags:
            errors.append(ValidationError(name, f"태그 어휘 밖: {sorted(unknown_tags)}"))
        policy = item.get("pet_policy") or {}
        if not policy.get("source_url"):
            errors.append(ValidationError(name, "pet_policy.source_url 이 없습니다"))
        if policy.get("policy_type") not in policy_values:
            errors.append(
                ValidationError(name, f"policy_type 이 enum 밖입니다: {policy.get('policy_type')}")
            )
    return errors


def resolve_coord(
    item: dict, geocoder=geocode_address
) -> tuple[Coordinate, bool]:
    """(좌표, 지오코딩했는지). 좌표가 있으면 그대로, 없으면 주소·장소명으로 찾는다."""

    latitude, longitude = item.get("latitude"), item.get("longitude")
    if latitude is not None and longitude is not None:
        return (float(latitude), float(longitude)), False
    query = item.get("address") or item.get("road_address") or item.get("name") or ""
    geocoded: GeocodedAddress = geocoder(query)
    return (geocoded.latitude, geocoded.longitude), True


def duplicate_reason(name: str, coord: Coordinate, existing: list[ExistingPlace]) -> str | None:
    """이미 있는 장소면 건너뛸 이유를, 아니면 None."""

    for place in existing:
        if place.name == name:
            return f"같은 이름 존재: {name}"
    for place in existing:
        if place.is_active and haversine_m(coord, place.coord) <= DUPLICATE_RADIUS_M:
            return f"100m 이내 활성 장소: {place.name}"
    return None


def load_items(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("landmarks.json 은 항목 배열이어야 합니다")
    return payload


def existing_places(db: Session) -> list[ExistingPlace]:
    rows = db.execute(
        select(Place.name, Place.latitude, Place.longitude, Place.is_active)
    ).all()
    return [
        ExistingPlace(name, (float(latitude), float(longitude)), is_active)
        for name, latitude, longitude, is_active in rows
    ]


def tag_code_to_id(db: Session) -> dict[str, int]:
    return {code: tag_id for tag_id, code in db.execute(select(PlaceTag.id, PlaceTag.code)).all()}


def _parse_verified_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=KST)


def insert_landmark(
    db: Session, item: dict, coord: Coordinate, code_to_id: dict[str, int]
) -> uuid.UUID:
    """장소·정책·태그를 함께 넣고 새 place_id 를 돌려준다."""

    environment = item.get("environment")
    place = Place(
        id=uuid.uuid4(),
        name=item["name"],
        category=item["category"],
        region=item["region"],
        address=item.get("address"),
        road_address=item.get("road_address"),
        latitude=Decimal(str(coord[0])),
        longitude=Decimal(str(coord[1])),
        homepage_url=item.get("homepage_url"),
        description=item.get("description"),
        description_source=DataProvider.INTERNAL,
        environment=PlaceEnvironment(environment) if environment else None,
        average_stay_minutes=item.get("average_stay_minutes")
        or default_stay_minutes(item["category"]),
        business_hours_raw=item.get("business_hours_raw"),
        created_by_user_id=None,
        is_active=True,
    )
    db.add(place)
    db.flush()

    policy = item["pet_policy"]
    max_weight = policy.get("max_weight_kg")
    db.add(
        PlacePetPolicy(
            place_id=place.id,
            policy_type=PetPolicyType(policy["policy_type"]),
            allowed_sizes=policy.get("allowed_sizes") or [],
            max_weight_kg=Decimal(str(max_weight)) if max_weight is not None else None,
            carrier_required=policy.get("carrier_required"),
            leash_required=policy.get("leash_required"),
            food_area_allowed=policy.get("food_area_allowed"),
            notes=policy.get("notes"),
            caution_note=policy.get("caution_note"),
            source=DataProvider.INTERNAL,
            source_url=policy.get("source_url"),
            verified_at=_parse_verified_at(policy.get("verified_at")),
            reliability_score=Decimal(POLICY_RELIABILITY),
        )
    )
    for code in dict.fromkeys(item.get("tags") or []):
        db.add(
            PlaceTagLink(
                place_id=place.id,
                tag_id=code_to_id[code],
                confidence=Decimal("1.000"),
                source=DataProvider.INTERNAL,
            )
        )
    return place.id


def write_ids(place_ids: list[uuid.UUID]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = Path(f"landmarks-seeded-{stamp}.txt")
    path.write_text("".join(f"{place_id}\n" for place_id in place_ids), encoding="utf-8")
    return path


def read_ids(path: Path) -> list[uuid.UUID]:
    return [
        uuid.UUID(line.strip())
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_seed(db: Session, path: Path, *, apply: bool) -> int:
    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    if not path.exists():
        print(f"입력 파일이 없습니다: {path}")
        return 1

    items = load_items(path)
    valid_codes = frozenset(tag_code_to_id(db))
    errors = validate(items, valid_codes)
    if errors:
        print(f"\n검증 실패 {len(errors)}건 — 아무것도 넣지 않습니다:")
        for error in errors:
            print(f"  {error.name}: {error.reason}")
        return 1

    print(f"입력 항목 : {len(items)}건", flush=True)
    print("좌표 확인·중복 조회 중...", flush=True)
    existing = existing_places(db)

    to_insert: list[tuple[dict, Coordinate]] = []
    skips: list[tuple[str, str]] = []
    geocoded = 0
    for item in items:
        coord, was_geocoded = resolve_coord(item)
        geocoded += was_geocoded
        reason = duplicate_reason(item["name"], coord, existing)
        if reason is not None:
            skips.append((item["name"], reason))
            continue
        to_insert.append((item, coord))
        # 같은 배치 안의 중복도 잡도록 방금 것을 기존 목록에 더한다.
        existing.append(ExistingPlace(item["name"], coord, True))

    print(f"\n넣을 명소 : {len(to_insert)}곳  (지오코딩 {geocoded}건, 건너뜀 {len(skips)}건)")
    for name, reason in skips:
        print(f"  건너뜀  {name} — {reason}")

    if not to_insert:
        print("\n넣을 것이 없습니다. 이미 반영되어 있습니다.")
        return 0
    if not apply:
        print("\n확인만 했습니다. 실제로 넣으려면 --apply 를 붙이세요.")
        return 0
    if is_shared_db() and not confirm(target, len(to_insert)):
        print("\n취소했습니다.")
        return 1

    code_to_id = tag_code_to_id(db)
    inserted = [insert_landmark(db, item, coord, code_to_id) for item, coord in to_insert]
    db.commit()
    path_out = write_ids(inserted)
    print(f"\n{len(inserted)}곳을 넣었습니다.")
    print(f"되돌릴 때 쓸 목록 : {path_out}")
    return 0


def run_revert(db: Session, path: Path) -> int:
    if not path.exists():
        print(f"파일이 없습니다: {path}")
        return 1
    ids = read_ids(path)
    target = describe_target()
    print(f"대상 DB : {target}", flush=True)
    print(f"되돌릴 명소 : {len(ids)}곳 ({path})", flush=True)
    if is_shared_db() and not confirm(target, len(ids)):
        print("\n취소했습니다.")
        return 1
    # 정책·태그는 FK ondelete CASCADE 로 함께 지워진다.
    result = db.execute(delete(Place).where(Place.id.in_(ids)))
    db.commit()
    print(f"\n{result.rowcount}곳을 삭제했습니다.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="path", type=Path, default=Path(DATA_DEFAULT))
    parser.add_argument("--apply", action="store_true", help="실제로 넣는다. 없으면 검증·조회만.")
    parser.add_argument(
        "--revert", type=Path, metavar="파일", help="--apply 가 남긴 목록의 장소를 삭제한다."
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.revert:
            return run_revert(db, args.revert)
        return run_seed(db, args.path, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
