"""places.category_detail 추출 (7.2 — etc 세부 분류).

**추출만** 한다(DB 불변). `category='etc'` 장소의 description 에 남아 있는
KCISA 원본 분류(`[KCISA 원본 분류] 반려동물업 > 반려의료 > 동물병원`)의 **말단**을
`category_detail` 제안으로 만든다. 반영은 `apply_place_batch.py`(화이트리스트·
IS NULL 가드) 재사용.

- 값은 **KCISA 말단 분류 한글 원문 그대로** — places.md 계약("예: etc 안의 동물약국·
  동물병원, 라벨 표기는 앱")과 일치. enum 이 아니며 코드로 바꾸지 않는다.
- 리허설 실측(2026-09-02): etc 278건 전량이 동물약국 126·동물병원 75·반려동물용품 51·
  미용 26 네 값으로 결정적 추출된다. 템플릿이 없는 행은 review_queue 로.

실행: `DATABASE_URL=... uv run python -m scripts.extract_category_detail [--out PATH]`
반영: `uv run python -m scripts.apply_place_batch \
      --in infra/batch/category_detail_staging.json [--apply]`
"""

import json
import re
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models import Place
from app.db.session import SessionLocal

OUT_DEFAULT = "infra/batch/category_detail_staging.json"

#: description 의 KCISA 분류 라인. 말단만 쓴다.
_KCISA_LINE = re.compile(r"\[KCISA 원본 분류\]([^\n]+)")

#: category_detail varchar(50) — 초과 값은 잘못 뽑힌 것으로 보고 review 로.
_MAX_LENGTH = 50


def extract_leaf(description: str | None) -> str | None:
    """description → KCISA 말단 분류. 템플릿이 없거나 말단이 비면 None.

    순수 함수 — 단위 테스트 대상.
    """
    if not description:
        return None
    match = _KCISA_LINE.search(description)
    if not match:
        return None
    leaf = match.group(1).split(">")[-1].strip()
    if not leaf or len(leaf) > _MAX_LENGTH:
        return None
    return leaf


def main() -> None:
    args = sys.argv[1:]
    out = args[args.index("--out") + 1] if "--out" in args else OUT_DEFAULT

    proposals: list[dict] = []
    review: list[dict] = []
    with SessionLocal() as db:
        rows = db.execute(
            select(Place.id, Place.description).where(
                Place.category == "etc", Place.category_detail.is_(None)
            )
        ).all()

    for place_id, description in rows:
        leaf = extract_leaf(description)
        if leaf is None:
            review.append(
                {
                    "table": "places",
                    "pk": str(place_id),
                    "column": "category_detail",
                    "reason": "KCISA 분류 템플릿 없음/말단 이상 — 수동 확인",
                    "evidence": (description or "")[:80],
                }
            )
            continue
        proposals.append(
            {
                "table": "places",
                "pk": str(place_id),
                "column": "category_detail",
                "current": None,
                "proposed": leaf,
                "reliability": 100,
                "method": "regex:kcisa-category",
                "evidence": (description or "")[:80],
            }
        )

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "note": "etc 세부 분류(category_detail) 제안. 반영은 apply_place_batch --in.",
        "proposal_count": len(proposals),
        "review_count": len(review),
        "proposals": proposals,
        "review_queue": review,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"제안 {len(proposals)}건 / 검수 큐 {len(review)}건 → {out}")


if __name__ == "__main__":
    main()