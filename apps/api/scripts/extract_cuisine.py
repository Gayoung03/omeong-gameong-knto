"""음식점·카페의 세부 음식 종류(cuisine)를 카카오 로컬 검색으로 유도해 스테이징한다.

restaurant·restaurant_cafe·cafe 중 cuisine 이 비어 있는 장소를 대상으로, 장소명+주소로
카카오 키워드 검색을 돌려 category_name("음식점 > 한식 > …")의 2단계를 cuisine 후보로
뽑는다. 검색 결과가 대상 장소와 **좌표 200m 이내**로 확인될 때만 제안한다(다른 가게의
분류가 섞이는 것을 막는다).

산출물은 apply_place_batch 형식의 스테이징 JSON 이다. 사람이 검수한 뒤
``apply_place_batch --apply --min-reliability 90`` 으로 반영한다(이 스크립트는 DB 를
바꾸지 않는다). 카카오 호출은 대상 수만큼 일어나므로 초당 10건 이하로 제한한다.

    cd apps/api && uv run python -m scripts.extract_cuisine --limit 20   # 표본
    cd apps/api && uv run python -m scripts.extract_cuisine              # 전체
"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Place
from app.db.session import SessionLocal
from app.integrations.maps.kakao import KakaoGeocodingError, search_places
from app.recommend.common.geo import haversine_m
from scripts.activate_kakao_places import describe_target

TARGET_CATEGORIES = ("restaurant", "restaurant_cafe", "cafe")
MATCH_RADIUS_M = 200.0
# 카카오 category_name 최상위가 이것일 때만 음식 분류로 인정한다.
FOOD_TOP_LEVEL = "음식점"
CUISINE_MAX_LENGTH = 30
RELIABILITY = 90
OUT_DEFAULT = "infra/batch/cuisine_staging.json"
DEFAULT_SLEEP_SECONDS = 0.11  # ≈9건/초 (카카오 초당 10건 제한 아래)


def parse_cuisine(category_name: str) -> str | None:
    """"음식점 > 한식 > 해물,생선" → "한식". 음식점 분류가 아니면 None."""
    parts = [part.strip() for part in category_name.split(">")]
    if len(parts) < 2 or parts[0] != FOOD_TOP_LEVEL or not parts[1]:
        return None
    return parts[1][:CUISINE_MAX_LENGTH]


def within_match_radius(
    place_coord: tuple[float, float], doc_coord: tuple[float, float]
) -> bool:
    return haversine_m(place_coord, doc_coord) <= MATCH_RADIUS_M


def target_places(db: Session, limit: int | None) -> list[Place]:
    statement = (
        select(Place)
        .where(Place.category.in_(TARGET_CATEGORIES), Place.cuisine.is_(None))
        .order_by(Place.id)
    )
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement))


def run(db: Session, *, limit: int | None, out: Path, sleep_seconds: float) -> int:
    print(f"대상 DB : {describe_target()}", flush=True)
    places = target_places(db, limit)
    print(f"대상 장소 : {len(places)}곳 (cuisine IS NULL, {'/'.join(TARGET_CATEGORIES)})")
    print(f"카카오 검색 중... (초당 최대 {round(1 / sleep_seconds)}건)", flush=True)

    proposals: list[dict] = []
    cuisines: Counter[str] = Counter()
    skips: Counter[str] = Counter()
    for index, place in enumerate(places):
        query = f"{place.name} {place.address or ''}".strip()
        try:
            found = search_places(query, size=1)
        except KakaoGeocodingError:
            skips["검색 실패"] += 1
            continue
        finally:
            if index < len(places) - 1:
                time.sleep(sleep_seconds)

        if not found:
            skips["결과 없음"] += 1
            continue
        doc = found[0]
        if not within_match_radius(
            (float(place.latitude), float(place.longitude)), (doc.latitude, doc.longitude)
        ):
            skips["200m 밖(불일치)"] += 1
            continue
        cuisine = parse_cuisine(doc.category_name)
        if cuisine is None:
            skips["음식 분류 아님"] += 1
            continue
        cuisines[cuisine] += 1
        proposals.append(
            {
                "table": "places",
                "column": "cuisine",
                "pk": str(place.id),
                "proposed": cuisine,
                "reliability": RELIABILITY,
            }
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"proposals": proposals}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n제안 : {len(proposals)}건 → {out}")
    print("cuisine 값 분포")
    for cuisine, count in cuisines.most_common():
        print(f"  {cuisine:<12} {count:>4}")
    if skips:
        print("건너뜀")
        for reason, count in skips.most_common():
            print(f"  {reason:<14} {count:>4}")
    print(
        "\n검수 후 반영: uv run python -m scripts.apply_place_batch "
        f"--in {out} --apply --min-reliability {RELIABILITY}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="대상 수 상한(표본 실행용).")
    parser.add_argument("--out", type=Path, default=Path(OUT_DEFAULT), help="스테이징 JSON 경로.")
    parser.add_argument(
        "--sleep", type=float, default=DEFAULT_SLEEP_SECONDS, help="호출 간격(초). 기본 0.11."
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        return run(db, limit=args.limit, out=args.out, sleep_seconds=args.sleep)


if __name__ == "__main__":
    sys.exit(main())
