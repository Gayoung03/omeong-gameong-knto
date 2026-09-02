"""가이드 body ↔ 운송 규정 값 정합 검사 (ai-io-column-design 7.5).

7.5는 "body 중복 서술은 유지하되 숫자가 규정 테이블과 어긋나지 않게 자동 검사"를
확정했다. DB 를 쓰지 않고 **시드 원본(scripts/seed_guides.py + data/guides/*.md)을
직접 대조**한다 — 실행 환경의 기존 데이터에 좌우되지 않고, 시드가 곧 정본이기 때문.

검사 방향은 "규정 값이 body 에 등장하는가"(중복 서술 원칙). body 가 그 값을 아예
서술하지 않기로 한 항목은 KNOWN_ABSENT 로 **명시**한다 — 집합이 실제와 어긋나면
(값을 body 에 새로 썼거나, 서술을 지웠거나) 테스트가 깨져 갱신을 강제한다.
"""

import re
from decimal import Decimal

import pytest

from scripts import seed_guides as sg

#: (단위 종류, 규정 dict 의 수치 필드) — 여기 없는 수치 필드가 생기면 커버리지 검사가 잡는다.
UNIT_FIELDS: dict[str, tuple[str, ...]] = {
    "kg": ("cabin_max_weight_kg", "cargo_max_weight_kg", "cargo_fee_threshold_kg"),
    "weeks": ("min_age_weeks_cabin", "min_age_weeks_cargo"),
    "krw": ("cabin_fee_krw", "cargo_fee_light_krw", "cargo_fee_heavy_krw",
            "airport_cage_price_krw"),
    "hours": ("request_deadline_hours",),
    "minutes": ("duration_minutes",),
    "pets": ("max_pets_per_person_cabin", "max_pets_per_trip"),
}
NUMERIC_FIELDS = frozenset(f for fields in UNIT_FIELDS.values() for f in fields)

#: body 가 의도적으로 서술하지 않는 (carrier_name, route, 필드) — 사유를 함께 적는다.
#: 여기 있는 항목이 body 에 등장하게 되면 테스트가 깨진다(목록 정리 강제).
KNOWN_ABSENT: frozenset[tuple[str, str | None, str]] = frozenset(
    {
        # 티웨이 body 는 사전 신청 필요만 말하고 마감 시각(24시간)은 서술하지 않는다.
        ("티웨이항공", None, "request_deadline_hours"),
        # 편당 총 마리수(6)는 개인이 어쩔 수 없는 선착순 상한이라 body 가 서술하지 않는다.
        ("제주항공", None, "max_pets_per_trip"),
        ("티웨이항공", None, "max_pets_per_trip"),
        ("이스타항공", None, "max_pets_per_trip"),
    }
)


def _num(value) -> str:
    f = float(value)
    return str(int(f)) if f == int(f) else str(f)


def _appears(body: str, unit: str, value) -> bool:
    n = _num(value)
    if unit == "kg":
        return re.search(rf"{n}\s*(?:kg|㎏)", body) is not None
    if unit == "weeks":
        return re.search(rf"{n}\s*주", body) is not None
    if unit == "krw":
        won = int(value)
        comma = f"{won:,}"
        # "30,000원" · "30000원" · "3만 원" 표기를 모두 허용한다.
        pats = [rf"(?:{comma}|{won})\s*원"]
        if won % 10000 == 0:
            pats.append(rf"{won // 10000}\s*만\s*원")
        return any(re.search(p, body) for p in pats)
    if unit == "hours":
        return re.search(rf"{n}\s*시간", body) is not None
    if unit == "pets":
        return re.search(rf"{n}\s*마리", body) is not None
    # minutes — "160분" 또는 "2시간 40분"/"2시간" 표기.
    total = int(value)
    hours, minutes = divmod(total, 60)
    pats = [rf"{total}\s*분"]
    if hours:
        pats.append(rf"{hours}\s*시간\s*{minutes}\s*분" if minutes else rf"{hours}\s*시간")
    return any(re.search(p, body) for p in pats)


def _rules() -> list[dict]:
    return [dict(spec) for spec in sg.TRANSPORT_RULES]


def test_규정의_수치_필드는_전부_커버리지_목록에_있다() -> None:
    for spec in _rules():
        numeric = {
            key for key, value in spec.items()
            if isinstance(value, (int, Decimal)) and not isinstance(value, bool)
        }
        unknown = numeric - NUMERIC_FIELDS
        assert not unknown, (
            f"{spec['carrier_name']}: UNIT_FIELDS 에 없는 수치 필드 {unknown} — "
            "정합 검사 대상에 추가하거나 제외 사유를 남기세요"
        )


def test_규정_값은_body와_어긋나지_않는다() -> None:
    failures: list[str] = []
    absences: set[tuple[str, str | None, str]] = set()
    for spec in _rules():
        body = sg._body(spec["doc"])
        key_base = (spec["carrier_name"], spec.get("route"))
        for unit, fields in UNIT_FIELDS.items():
            for field in fields:
                value = spec.get(field)
                if value is None:
                    continue
                # "1마리"는 본문이 단수 서술("함께 탈 수 있어요")로 갈음한다 — 전 항공사 공통.
                if unit == "pets" and int(value) == 1:
                    continue
                if _appears(body, unit, value):
                    continue
                entry = (*key_base, field)
                if entry in KNOWN_ABSENT:
                    absences.add(entry)
                else:
                    failures.append(f"{entry}: 규정 {field}={value} 가 body 에 없다")
    assert not failures, "\n".join(failures)
    # KNOWN_ABSENT 가 실제보다 크면(=body 에 값이 생겼으면) 목록을 정리해야 한다.
    stale = KNOWN_ABSENT - absences
    assert not stale, f"KNOWN_ABSENT 에서 지워야 할 항목: {stale}"


def test_모든_body는_적재_계약_길이_이내다() -> None:
    for slug, *_ in sg.GUIDE_DOCUMENTS:
        body = sg._body(slug)
        assert len(body) <= sg.BODY_MAX_CHARS, f"{slug}: {len(body)}자 > {sg.BODY_MAX_CHARS}"


def test_규정이_가리키는_문서는_모두_존재한다() -> None:
    slugs = {slug for slug, *_ in sg.GUIDE_DOCUMENTS}
    for spec in _rules():
        assert spec["doc"] in slugs, f"운송 규정이 없는 문서를 가리킴: {spec['doc']}"


def test_본문_적재_계약_초과는_거부된다(tmp_path, monkeypatch) -> None:
    over = tmp_path / "too-long.md"
    over.write_text("가" * (sg.BODY_MAX_CHARS + 1), encoding="utf-8")
    monkeypatch.setattr(sg, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match="적재 계약"):
        sg._body("too-long")