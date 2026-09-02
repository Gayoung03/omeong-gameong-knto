"""place_business_hours.raw_text → places.business_hours_raw 이관 제안 추출 (7.3·8.1).

**추출만** 한다(DB 불변). raw_text 드롭(8.1 ④)의 선행물로, 장소당 1값을
`places.business_hours_raw` 에 채울 제안을 만든다. 반영은 기존 파이프라인
(`apply_place_batch.py`)이 담당한다 — 화이트리스트·`WHERE IS NULL` 가드·dry-run 상속.

- 같은 장소의 요일 행들이 `ㅣ` 정규화 후에도 **서로 다른 텍스트**면 자동 제안하지 않고
  `review_queue` 로 뺀다 (8.1: 요일별 상이 텍스트 손실 차단. 리허설 실측 0건 — 안전장치).
- 이미 `business_hours_raw` 가 있는 장소는 대상에서 뺀다(재적재 방지 — apply 가드와 이중).
- 파싱 배치 스테이징과 **파일을 공유하지 않는다**(검수 흐름 분리 — 계획 리뷰 반영).

실행: `DATABASE_URL=... uv run python -m scripts.extract_business_hours_raw [--out PATH]`
반영: `uv run python -m scripts.apply_place_batch \
      --in infra/batch/business_hours_raw_staging.json [--apply]`
      ※ 실DB 반영은 8.1 순서상 ①(places.md 계약 갱신·프론트 조율)·②(응답 raw_text 참조
      제거 배포) **이후에만** — 먼저 채우면 이중 진실원본 기간만 늘어난다.
"""

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models import Place, PlaceBusinessHour
from app.db.session import SessionLocal
from scripts.notes_parsing import normalize_bar

OUT_DEFAULT = "infra/batch/business_hours_raw_staging.json"


def group_raw_texts(rows: list[tuple[str, str]]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """(place_id, raw_text) 목록 → (장소당 단일 정규화 텍스트, 상이 텍스트 장소별 목록).

    순수 함수 — 단위 테스트 대상. 정규화(`ㅣ`→공백·연속 공백 축약) 후에도 한 장소에
    서로 다른 값이 남으면 두 번째 반환값(review 대상)으로 분류한다.
    """
    by_place: dict[str, set[str]] = defaultdict(set)
    for place_id, raw in rows:
        normalized = normalize_bar(raw).strip()
        if normalized:
            by_place[place_id].add(normalized)
    single = {pid: next(iter(texts)) for pid, texts in by_place.items() if len(texts) == 1}
    multi = {pid: sorted(texts) for pid, texts in by_place.items() if len(texts) > 1}
    return single, multi


def main() -> None:
    args = sys.argv[1:]
    out = args[args.index("--out") + 1] if "--out" in args else OUT_DEFAULT

    with SessionLocal() as db:
        rows = [
            (str(place_id), raw)
            for place_id, raw in db.execute(
                select(PlaceBusinessHour.place_id, PlaceBusinessHour.raw_text).where(
                    PlaceBusinessHour.raw_text.isnot(None)
                )
            )
        ]
        already = {
            str(pid)
            for pid in db.scalars(
                select(Place.id).where(Place.business_hours_raw.isnot(None))
            )
        }

    single, multi = group_raw_texts(rows)
    proposals = [
        {
            "table": "places",
            "pk": pid,
            "column": "business_hours_raw",
            "current": None,
            "proposed": text,
            "reliability": 100,
            "method": "regex:hours-raw-migrate",
            "evidence": text[:80],
        }
        for pid, text in sorted(single.items())
        if pid not in already
    ]
    review = [
        {
            "table": "places",
            "pk": pid,
            "column": "business_hours_raw",
            "reason": "요일별 raw_text 상이 — 수동 확인",
            "variants": texts,
        }
        for pid, texts in sorted(multi.items())
    ]

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "note": "raw_text→places.business_hours_raw 이관 제안. 반영은 apply_place_batch --in.",
        "proposal_count": len(proposals),
        "review_count": len(review),
        "proposals": proposals,
        "review_queue": review,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    skipped = len(single) - len(proposals)
    print(f"제안 {len(proposals)}건 / 검수 큐 {len(review)}건 / 기존 값 스킵 {skipped}건 → {out}")


if __name__ == "__main__":
    main()