"""notes·영업시간 raw_text 정규식 파싱 (Cycle B 배치, ai-io-column-design 8.1).

**정규식 결정적 추출만** 담는다(reliability=100). 자유문 복합 추출은 LLM 단계(별도)다.
순수 함수라 DB 없이 단위 테스트한다. 실 데이터 샘플 기준으로 패턴을 맞췄다.

이중 시점(`[기존 정책]`/`[KCISA]`) 규칙: **최신 = [KCISA]**(재수집 블록). 기존 블록에만
있는 정보는 버리지 않고 보조로 유지, 두 블록이 직접 모순이면 자동 적용하지 않고 검수 큐로.
"""

import re
from datetime import time
from decimal import Decimal

# ㅣ (U+3163 HANGUL LETTER I) 가 구분자로 잘못 쓰인 깨진 텍스트. 공백으로 정규화.
BAR = "ㅣ"

KCISA_MARK = "[KCISA]"
LEGACY_MARK = "[기존 정책]"

SIZE_MAP = {"소형견": "small", "중형견": "medium", "대형견": "large"}
ALL_SIZES = ["small", "medium", "large"]


def normalize_bar(text: str | None) -> str | None:
    """`ㅣ` 구분자를 공백으로 바꾸고 연속 공백을 하나로 줄인다."""
    if text is None:
        return None
    return re.sub(r"[ \t]+", " ", text.replace(BAR, " ")).strip()


def split_blocks(notes: str | None) -> tuple[str | None, str | None]:
    """이중 시점 notes 를 (kcisa_block, legacy_block) 로 분리한다.

    마크가 없으면 (notes, None). KCISA 만 있으면 (kcisa, None).
    기존 정책만 있으면 (None, legacy).
    """
    if notes is None:
        return None, None
    if KCISA_MARK not in notes and LEGACY_MARK not in notes:
        return notes, None

    kcisa = legacy = None
    if KCISA_MARK in notes:
        after = notes.split(KCISA_MARK, 1)[1]
        # 다음 마크 전까지가 KCISA 블록.
        kcisa = after.split(LEGACY_MARK, 1)[0].strip()
    if LEGACY_MARK in notes:
        after = notes.split(LEGACY_MARK, 1)[1]
        legacy = after.split(KCISA_MARK, 1)[0].strip()
    return kcisa or None, legacy or None


def parse_kcisa_kv(block: str | None) -> dict[str, str]:
    """'키: 값' 줄들을 dict 로. 값의 앞뒤 공백·`ㅣ` 정규화."""
    result: dict[str, str] = {}
    if not block:
        return result
    for line in normalize_bar(block).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if key and val:
                result[key] = val
    return result


def extract_sizes(text: str | None) -> list[str] | None:
    """'모두 가능' → 전체 / '소형견'·'중형견'·'대형견' 언급 → 해당 목록."""
    if not text:
        return None
    if "모두 가능" in text:
        return list(ALL_SIZES)
    found = [code for label, code in SIZE_MAP.items() if label in text]
    return found or None


def extract_max_weight_kg(text: str | None) -> Decimal | None:
    """'N kg 이하/미만' → N. '이상'은 상한이 아니므로 잡지 않는다."""
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*kg\s*(?:이하|미만)", text)
    return Decimal(m.group(1)) if m else None


def extract_max_pets(text: str | None) -> int | None:
    """'N마리' → N. 없으면 깨진 표기 'NM 이내'(=N마리) 를 보조로 인식한다."""
    if not text:
        return None
    m = re.search(r"(\d+)\s*마리", text)
    if m:
        return int(m.group(1))
    # 'N마리' 의 깨진 표기(2M 이내 등) — 알려진 데이터 오류 보정.
    m = re.search(r"(\d+)\s*M\s*이내", text)
    return int(m.group(1)) if m else None


def extract_muzzle_required(text: str | None) -> bool | None:
    """'입마개' 언급 시 True. 언급 없으면 None(미확인 — False 로 단정하지 않음)."""
    if not text:
        return None
    return True if "입마개" in text else None


def extract_food_area_allowed(text: str | None) -> bool | None:
    """'식음료 공간 … 불가' → False. 명시 없으면 None."""
    if not text:
        return None
    if re.search(r"식음료\s*공간.*(?:불가|금지|제한)", text):
        return False
    return None


_HOURS_RE = re.compile(r"(\d{1,2}):(\d{2})\s*[-~]\s*(\d{1,2}):(\d{2})")


def parse_hours(raw_text: str | None) -> tuple[time | None, time | None]:
    """'HH:MM-HH:MM' 첫 구간을 (opens, closes) 로. 입장마감 등 단독 시각은 무시."""
    text = normalize_bar(raw_text)
    if not text:
        return None, None
    m = _HOURS_RE.search(text)
    if not m:
        return None, None
    oh, om, ch, cm = (int(g) for g in m.groups())
    if oh > 23 or ch > 23 or om > 59 or cm > 59:
        return None, None
    return time(oh, om), time(ch, cm)


def parse_check_in_out(raw_text: str | None) -> tuple[time | None, time | None]:
    """'입실/체크인 … HH:MM', '퇴실/체크아웃 … HH:MM' → (check_in, check_out)."""
    text = normalize_bar(raw_text)
    if not text:
        return None, None

    def _find(labels: tuple[str, ...]) -> time | None:
        for label in labels:
            m = re.search(label + r"[^0-9]{0,6}(\d{1,2}):(\d{2})", text)
            if m:
                h, mn = int(m.group(1)), int(m.group(2))
                if h <= 23 and mn <= 59:
                    return time(h, mn)
        return None

    return _find(("입실", "체크인")), _find(("퇴실", "체크아웃"))
