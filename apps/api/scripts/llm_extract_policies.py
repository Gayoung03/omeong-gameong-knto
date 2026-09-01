"""자유문 notes → 구조화 (LLM 보조 단계, ai-io-column-design 8.1).

정규식(extract_place_batch)이 못 잡는 복합 자유문("체고 40cm·체중 10kg·생후 3개월·
1마리")을 gpt-4o-mini(temp 0)로 구조화하고, caution_note(150자)를 정제한다.
결과는 스테이징 JSON(reliability=70)에 담아 apply_place_batch 가 검수 후 반영한다.

원칙
- **추출 실패는 null**(추측 금지). 어휘 enum 으로 값 제한(개인 서사·과추출 방지).
- **PII 스팟체크**: 연락처/주민번호류 패턴이 보이는 자유문은 LLM 에 보내지 않고 별도
  목록(pii_flagged)으로 뺀다. 원문은 로그에 남기지 않는다(발췌·길이만).
- 대상 컬럼이 현재 NULL 인 것만 제안(재적재 방지). 최신 블록(KCISA) 우선.

핵심 로직(build_llm_proposals·detect_pii)은 순수 함수라 LLM 없이 단위 테스트한다.

실행(DATABASE_URL·OPENAI_API_KEY 필요, 로컬/리허설 대상):
    uv run python -m scripts.llm_extract_policies [--out PATH] [--limit N]
"""

import json
import os
import re
import sys

from sqlalchemy import or_, select

from app.core.config import settings
from app.db.models import PlacePetPolicy
from app.db.session import SessionLocal
from scripts import notes_parsing as np

OUT_DEFAULT = "infra/batch/place_batch_llm_staging.json"

# 정규식이 이미 담당하는 필드 외의 복합 정보가 있을 법한 자유문만 LLM 으로.
FREE_TEXT_HINTS = ("체고", "체중", "생후", "개월", "이내", "이하", "미만", "마리", "동반")

# PII 스팟체크: 전화번호·주민번호류. (원문은 로그 미기록)
PII_RE = re.compile(r"(01[016-9][-\s]?\d{3,4}[-\s]?\d{4})|(\d{6}[-\s]?[1-4]\d{6})")

# 추출 대상 컬럼(어휘 enum 제한은 LLM 스키마에서).
LLM_FIELDS = ["allowed_sizes", "max_weight_kg", "max_pets_per_person",
              "muzzle_required", "food_area_allowed", "caution_note"]

CAUTION_MAX = 150


def detect_pii(text: str | None) -> bool:
    return bool(text and PII_RE.search(text))


def build_llm_proposals(pk: str, current: dict, llm_result: dict, evidence: str) -> list[dict]:
    """LLM 추출 결과 → 제안 목록. 대상 컬럼이 NULL 이고 값이 있을 때만."""
    proposals: list[dict] = []
    for col in LLM_FIELDS:
        if current.get(col) is not None:
            continue
        val = llm_result.get(col)
        if val is None or (isinstance(val, list) and not val):
            continue
        if col == "caution_note":
            val = str(val)[:CAUTION_MAX]
        proposals.append({
            "table": "place_pet_policies", "pk": pk, "column": col,
            "current": None, "proposed": val,
            "reliability": 70, "method": "llm", "evidence": evidence[:80],
        })
    return proposals


def _extraction_tool() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "extract_pet_policy",
            "description": "자유문에서 구조화 값을 뽑는다. 없거나 불확실하면 null.",
            "parameters": {
                "type": "object",
                "properties": {
                    "allowed_sizes": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["small", "medium", "large"]},
                    },
                    "max_weight_kg": {"type": ["number", "null"]},
                    "max_pets_per_person": {"type": ["integer", "null"]},
                    "muzzle_required": {"type": ["boolean", "null"]},
                    "food_area_allowed": {"type": ["boolean", "null"]},
                    "caution_note": {"type": ["string", "null"],
                                     "description": "핵심 주의사항 한 줄(≤150자), 없으면 null."},
                },
                "required": [],
            },
        },
    }


def _call_llm(text: str) -> dict:
    """OpenAI 로 구조화 추출. 실패·불확실은 빈 dict/null. (테스트에서 monkeypatch)"""
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, timeout=30, max_retries=1)
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": (
                "너는 반려동물 동반 정책 추출기다. 주어진 자유문에서 크기·무게·마리수·"
                "입마개·식음료 공간 가능 여부·주의사항을 뽑는다. 문서에 없거나 불확실하면 "
                "반드시 null(추측 금지). 개인정보·연락처는 절대 넣지 않는다."
            )},
            {"role": "user", "content": text},
        ],
        tools=[_extraction_tool()],
        tool_choice={"type": "function", "function": {"name": "extract_pet_policy"}},
    )
    calls = completion.choices[0].message.tool_calls
    if not calls:
        return {}
    try:
        return json.loads(calls[0].function.arguments)
    except (json.JSONDecodeError, TypeError):
        return {}


def main() -> None:
    args = sys.argv[1:]
    out = args[args.index("--out") + 1] if "--out" in args else OUT_DEFAULT
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY 가 필요합니다(로컬 .env).")

    proposals: list[dict] = []
    pii_flagged: list[dict] = []
    processed = 0
    with SessionLocal() as db:
        rows = db.scalars(
            select(PlacePetPolicy).where(
                PlacePetPolicy.notes.isnot(None),
                or_(
                    PlacePetPolicy.allowed_sizes.is_(None),
                    PlacePetPolicy.max_weight_kg.is_(None),
                    PlacePetPolicy.max_pets_per_person.is_(None),
                    PlacePetPolicy.caution_note.is_(None),
                ),
            )
        ).all()
        for r in rows:
            kcisa, legacy = np.split_blocks(r.notes)
            text = np.normalize_bar(kcisa or r.notes or "")
            if not any(h in text for h in FREE_TEXT_HINTS):
                continue
            if detect_pii(text):
                pii_flagged.append({"pk": str(r.id), "len": len(text), "reason": "PII패턴"})
                continue
            if limit is not None and processed >= limit:
                break
            processed += 1
            current = {c: getattr(r, c) for c in LLM_FIELDS}
            result = _call_llm(text)
            proposals.extend(build_llm_proposals(str(r.id), current, result, text))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "note": "LLM 추출(reliability=70). 검수 후 apply --min-reliability 70.",
            "processed": processed, "proposal_count": len(proposals),
            "pii_flagged_count": len(pii_flagged),
            "proposals": proposals, "pii_flagged": pii_flagged,
        }, f, ensure_ascii=False, indent=2)
    print(f"LLM 처리 {processed}건 / 제안 {len(proposals)}건 / PII 제외 {len(pii_flagged)}건")


if __name__ == "__main__":
    main()
