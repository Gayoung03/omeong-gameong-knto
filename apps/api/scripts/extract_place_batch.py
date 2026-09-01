"""notes·영업시간 정규식 추출 → 스테이징 JSON (Cycle B 배치, ai-io-column-design 8.1).

**추출만** 한다(DB 를 바꾸지 않음). 결과를 스테이징 JSON 에 모아 사람이 검수한 뒤
apply_place_batch.py 가 반영한다. 정규식 결정적 추출(reliability=100)만 담고, 자유문
복합 추출은 LLM 단계(별도)에서 이 JSON 에 덧붙인다.

- 이중 시점(`[KCISA]`/`[기존 정책]`): **KCISA 우선**. 두 블록이 같은 필드에서 **직접 모순**이면
  자동 제안하지 않고 `review_queue` 로 뺀다. 기존 블록에만 있는 값은 보조로 제안(method 표시).
- 제안은 대상 컬럼이 현재 NULL 인 것만(재적재 방지). 원문은 로그에 evidence 발췌만.

산출물: `infra/batch/place_batch_staging.json` (gitignore, 실데이터 포함 커밋 금지).

실행: `DATABASE_URL=... uv run python -m scripts.extract_place_batch [--out PATH]`
(로컬/리허설 DB 대상 권장 — 검수 후 apply 로 프로덕션 반영)
"""

import json
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models import PlaceBusinessHour, PlacePetPolicy
from app.db.session import SessionLocal
from scripts import notes_parsing as np

OUT_DEFAULT = "infra/batch/place_batch_staging.json"

# place_pet_policies 정규식 추출기: (컬럼, 함수, 직렬화)
POLICY_FIELDS = [
    ("allowed_sizes", np.extract_sizes, lambda v: v),
    ("max_weight_kg", np.extract_max_weight_kg, lambda v: float(v)),
    ("max_pets_per_person", np.extract_max_pets, lambda v: v),
    ("muzzle_required", np.extract_muzzle_required, lambda v: v),
    ("food_area_allowed", np.extract_food_area_allowed, lambda v: v),
]


def _evidence(text: str, limit: int = 80) -> str:
    return np.normalize_bar(text)[:limit] if text else ""


def _extract_policies(db, proposals, review):
    rows = db.scalars(
        select(PlacePetPolicy).where(PlacePetPolicy.notes.isnot(None))
    ).all()
    for r in rows:
        kcisa, legacy = np.split_blocks(r.notes)
        primary = kcisa if kcisa is not None else (r.notes if legacy is None else None)

        for col, fn, ser in POLICY_FIELDS:
            if getattr(r, col) is not None:
                continue  # 재적재 방지(이미 값 있음)
            val_p = fn(primary) if primary is not None else None
            val_l = fn(legacy) if legacy is not None else None

            # 이중 시점 직접 모순 → 검수 큐
            if kcisa is not None and legacy is not None:
                vk, vl = fn(kcisa), fn(legacy)
                if vk is not None and vl is not None and vk != vl:
                    review.append({
                        "table": "place_pet_policies", "pk": str(r.id), "column": col,
                        "reason": "이중 시점 모순(KCISA vs 기존)",
                        "kcisa": ser(vk), "legacy": ser(vl),
                    })
                    continue

            chosen, method, block = None, None, None
            if val_p is not None:
                chosen, method, block = val_p, "regex", "kcisa" if kcisa else "notes"
            elif val_l is not None:
                chosen, method, block = val_l, "regex:legacy_fallback", "legacy"

            if chosen is not None:
                proposals.append({
                    "table": "place_pet_policies", "pk": str(r.id), "column": col,
                    "current": None, "proposed": ser(chosen),
                    "reliability": 100, "method": method, "source_block": block,
                    "evidence": _evidence(kcisa or legacy or r.notes),
                })


def _extract_hours(db, proposals, review):
    rows = db.scalars(
        select(PlaceBusinessHour).where(PlaceBusinessHour.raw_text.isnot(None))
    ).all()
    for r in rows:
        # 영업시간 opens/closes (place_business_hours)
        opens, closes = np.parse_hours(r.raw_text)
        if r.opens_at is None and opens is not None:
            proposals.append({
                "table": "place_business_hours", "pk": str(r.id), "column": "opens_at",
                "current": None, "proposed": opens.isoformat(),
                "reliability": 100, "method": "regex:hours", "evidence": _evidence(r.raw_text),
            })
        if r.closes_at is None and closes is not None:
            proposals.append({
                "table": "place_business_hours", "pk": str(r.id), "column": "closes_at",
                "current": None, "proposed": closes.isoformat(),
                "reliability": 100, "method": "regex:hours", "evidence": _evidence(r.raw_text),
            })
        # 숙박 체크인/아웃 (places) — raw_text 에 입실/퇴실이 있으면 그 장소로 제안
        cin, cout = np.parse_check_in_out(r.raw_text)
        for col, val in (("check_in_time", cin), ("check_out_time", cout)):
            if val is not None:
                proposals.append({
                    "table": "places", "pk": str(r.place_id), "column": col,
                    "current": "?", "proposed": val.isoformat(),
                    "reliability": 100, "method": "regex:checkinout",
                    "evidence": _evidence(r.raw_text),
                })


def main() -> None:
    out = OUT_DEFAULT
    args = sys.argv[1:]
    if "--out" in args:
        out = args[args.index("--out") + 1]

    proposals: list[dict] = []
    review: list[dict] = []
    with SessionLocal() as db:
        _extract_policies(db, proposals, review)
        _extract_hours(db, proposals, review)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "note": "정규식 추출(reliability=100). 검수 후 apply_place_batch.py 로 반영.",
        "proposal_count": len(proposals),
        "review_count": len(review),
        "proposals": proposals,
        "review_queue": review,
    }
    import os

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    by_col: dict[str, int] = {}
    for p in proposals:
        by_col[f"{p['table']}.{p['column']}"] = by_col.get(f"{p['table']}.{p['column']}", 0) + 1
    print(f"제안 {len(proposals)}건 / 검수 큐 {len(review)}건 → {out}")
    for k, v in sorted(by_col.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
