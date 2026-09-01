"""스테이징 JSON(검수 완료) → DB 반영 (Cycle B 배치, ai-io-column-design 8.1).

extract_place_batch.py 가 만든 제안을 사람이 검수한 뒤 이 스크립트로 반영한다.

- **재적재 방지 가드**: `WHERE <col> IS NULL` — 이미 값이 있으면 건너뛴다(멱등).
- **review_queue 는 반영하지 않는다**(모순·수동 확인 대상).
- `--min-reliability`(기본 100): 이 값 미만 제안은 건너뜀. 정규식(100)만 기본 적용,
  LLM(70)은 검수 후 `--min-reliability 70` 로 명시할 때만.
- **기본 dry-run**, `--apply` 로 실제 UPDATE.

실행(DATABASE_URL 지정):
    uv run python -m scripts.apply_place_batch [--in PATH] [--apply] [--min-reliability N]
"""

import json
import sys
from datetime import time
from decimal import Decimal

from sqlalchemy import text

from app.db.session import SessionLocal

IN_DEFAULT = "infra/batch/place_batch_staging.json"

# 화이트리스트: 이 테이블·컬럼만 UPDATE 허용(임의 컬럼 주입 차단).
ALLOWED = {
    "place_pet_policies": {
        "allowed_sizes", "max_weight_kg", "max_pets_per_person",
        "muzzle_required", "food_area_allowed", "caution_note",
    },
    "place_business_hours": {"opens_at", "closes_at"},
    "places": {"check_in_time", "check_out_time", "category_detail", "business_hours_raw"},
}


def _deserialize(col: str, v):
    if col in {"opens_at", "closes_at", "check_in_time", "check_out_time"}:
        return time.fromisoformat(v)
    if col == "max_weight_kg":
        return Decimal(str(v))
    if col == "max_pets_per_person":
        return int(v)
    if col in {"muzzle_required", "food_area_allowed"}:
        return bool(v)
    return v  # allowed_sizes(list)·caution_note·category_detail·business_hours_raw(str)


def main() -> None:
    args = sys.argv[1:]
    path = args[args.index("--in") + 1] if "--in" in args else IN_DEFAULT
    apply = "--apply" in args
    min_rel = int(args[args.index("--min-reliability") + 1]) if "--min-reliability" in args else 100

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    proposals = payload["proposals"]

    skipped_rel = 0
    applied = skipped_guard = 0
    by_col: dict[str, int] = {}
    with SessionLocal() as db:
        for p in proposals:
            tbl, col = p["table"], p["column"]
            if col not in ALLOWED.get(tbl, set()):
                raise SystemExit(f"허용되지 않은 대상: {tbl}.{col}")
            if p.get("reliability", 0) < min_rel:
                skipped_rel += 1
                continue
            key = f"{tbl}.{col}"
            by_col[key] = by_col.get(key, 0) + 1
            if apply:
                val = _deserialize(col, p["proposed"])
                res = db.execute(
                    text(f"UPDATE {tbl} SET {col} = :val WHERE id = :pk AND {col} IS NULL"),
                    {"val": val, "pk": p["pk"]},
                )
                if res.rowcount:
                    applied += 1
                else:
                    skipped_guard += 1
        if apply:
            db.commit()

    mode = "적용" if apply else "DRY-RUN"
    print(f"{mode}: 대상 제안 {sum(by_col.values())}건 (신뢰도 <{min_rel} 제외 {skipped_rel}건)")
    for k, v in sorted(by_col.items()):
        print(f"  {k}: {v}")
    if apply:
        print(f"→ 반영 {applied}건 / 가드로 건너뜀(이미 값 있음) {skipped_guard}건")
    else:
        print("실제 반영하려면 --apply 를 붙이세요. review_queue 는 반영되지 않습니다(수동 확인).")


if __name__ == "__main__":
    main()
