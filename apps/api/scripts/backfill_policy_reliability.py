"""파싱 배치가 이미 채운 place_pet_policies 행의 reliability_score·verified_at 소급 백필.

설계 7.1은 두 컬럼을 "파싱 배치에서 채움"으로 확정했지만, 2026-09-02 실행분은 값만
쓰고 신뢰도·검증일을 남기지 않았다(계획 리뷰 발견). 이 스크립트는 그때 쓴 **검수본
스테이징 JSON**을 입력으로, "지금 DB 값 == 그때 제안값"인 행에만 소급 기록한다 —
그 이후 사람이 고친 행을 배치 딱지로 덮지 않기 위해서다.

- 한 행에 정규식(100)·LLM(70) 제안이 섞였으면 **낮은 쪽(70)** 을 쓴다(보수적).
- 수동 검수로 넣은 3건(검수 큐 KCISA 채택·정정)은 사람 검수 = 100 으로 함께 기록.
- 멱등: `reliability_score IS NULL` 인 행만. verified_at 도 비어 있을 때만.
- 기본 dry-run, `--apply` 로 반영. 향후 배치는 apply_place_batch 가 값과 함께
  기록하므로 이 스크립트는 소급용 1회성이다.

실행:
    uv run python -m scripts.backfill_policy_reliability \
        --in infra/batch/place_batch_staging_reviewed.json \
        --in infra/batch/place_batch_llm_reviewed.json [--apply]
"""

import json
import sys
from collections import defaultdict

from sqlalchemy import text

from app.db.session import SessionLocal
from scripts.apply_place_batch import ALLOWED, _deserialize

#: 검수 큐를 사람이 판정해 수동 UPDATE 한 행 — (pk, column, 넣은 값). 사람 검수 = 100.
#: 근거: 2026-09-02 검수 기록 (KCISA "객실당 최대 3/2마리" 채택, ②는 원문 대조로
#: [large]→[small] 정정).
MANUAL_REVIEWED = [
    ("13ae09da-6493-5e33-970c-1cf6e0f90993", "max_pets_per_person", 3),
    ("1bbaabe6-374a-5cdb-9a8a-bd4bce84b489", "allowed_sizes", ["small"]),
    ("6682577b-0772-5760-861b-b6b989f4ea59", "max_pets_per_person", 2),
]

#: 배열 컬럼은 varchar[] 라 바인딩(text[])과 직접 비교하면 타입 오류 — 캐스트해 비교.
_ARRAY_COLUMNS = {"allowed_sizes"}


def _matches(db, pk: str, column: str, proposed) -> bool:
    """지금 DB 값이 제안값과 같은가 — 배치가 쓴 값인지(또는 동일 판정인지) 확인."""
    # 컬럼명이 SQL 에 직접 들어가므로 화이트리스트 밖이면 어떤 입력도 실행하지 않는다
    # (apply_place_batch 와 같은 "임의 컬럼 주입 차단" — 코드 리뷰 반영).
    if column not in ALLOWED["place_pet_policies"]:
        raise SystemExit(f"허용되지 않은 컬럼: place_pet_policies.{column}")
    cast = "::text[]" if column in _ARRAY_COLUMNS else ""
    row = db.execute(
        text(f"SELECT 1 FROM place_pet_policies WHERE id = :pk AND {column}{cast} = :val"),
        {"pk": pk, "val": _deserialize(column, proposed)},
    ).first()
    return row is not None


def collect_scores(payloads: list[dict]) -> dict[str, tuple[int, list[tuple[str, object]]]]:
    """스테이징들 → pk 별 (최저 신뢰도, [(컬럼, 제안값), ...]). 순수 함수."""
    scores: dict[str, int] = {}
    values: dict[str, list[tuple[str, object]]] = defaultdict(list)
    for payload in payloads:
        for p in payload["proposals"]:
            if p["table"] != "place_pet_policies":
                continue
            if p["column"] not in ALLOWED["place_pet_policies"]:
                raise SystemExit(f"허용되지 않은 대상: place_pet_policies.{p['column']}")
            pk = p["pk"]
            rel = int(p.get("reliability", 100))
            scores[pk] = min(scores.get(pk, 100), rel)
            values[pk].append((p["column"], p["proposed"]))
    return {pk: (scores[pk], values[pk]) for pk in scores}


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    paths = [args[i + 1] for i, a in enumerate(args) if a == "--in"]
    if not paths:
        raise SystemExit("--in <스테이징.json> 을 하나 이상 지정하세요.")

    payloads = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            payloads.append(json.load(f))
    candidates = collect_scores(payloads)

    planned = 0
    skipped_mismatch = skipped_scored = 0
    with SessionLocal() as db:
        for pk, (rel, cols) in sorted(candidates.items()):
            already = db.execute(
                text("SELECT reliability_score FROM place_pet_policies WHERE id = :pk"),
                {"pk": pk},
            ).first()
            if already is None or already[0] is not None:
                skipped_scored += 1
                continue
            # 그 행에 제안했던 컬럼 중 **하나라도** 지금 값이 제안값과 같아야 소급한다.
            if not any(_matches(db, pk, col, val) for col, val in cols):
                skipped_mismatch += 1
                continue
            planned += 1
            if apply:
                db.execute(
                    text(
                        "UPDATE place_pet_policies SET reliability_score = :rel, "
                        "verified_at = COALESCE(verified_at, now()) "
                        "WHERE id = :pk AND reliability_score IS NULL"
                    ),
                    {"rel": rel, "pk": pk},
                )

        manual = 0
        for pk, column, value in MANUAL_REVIEWED:
            if not _matches(db, pk, column, value):
                continue
            pending = db.execute(
                text(
                    "SELECT 1 FROM place_pet_policies "
                    "WHERE id = :pk AND reliability_score IS NULL"
                ),
                {"pk": pk},
            ).first()
            if pending is None:
                continue
            manual += 1
            if apply:
                db.execute(
                    text(
                        "UPDATE place_pet_policies SET reliability_score = 100, "
                        "verified_at = COALESCE(verified_at, now()) "
                        "WHERE id = :pk AND reliability_score IS NULL"
                    ),
                    {"pk": pk},
                )

        if apply:
            db.commit()

    mode = "적용" if apply else "DRY-RUN"
    print(
        f"{mode}: 배치분 {planned}건 + 수동 검수분 {manual}건 "
        f"(이미 기록 {skipped_scored} / 값 불일치 제외 {skipped_mismatch})"
    )
    if not apply:
        print("실제 반영하려면 --apply 를 붙이세요.")


if __name__ == "__main__":
    main()