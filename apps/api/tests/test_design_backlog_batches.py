"""설계 잔여 배치(D1·D2·D4)의 순수 로직 단위 테스트 + apply 신뢰도 기록 통합 테스트."""

import uuid

from sqlalchemy.orm import Session

from scripts.backfill_policy_reliability import collect_scores
from scripts.extract_business_hours_raw import group_raw_texts
from scripts.extract_category_detail import extract_leaf

# ---------------------------------------------------------------------------
# D1 — raw_text 그룹핑
# ---------------------------------------------------------------------------


def test_요일_행이_같은_텍스트면_한_값으로_모인다() -> None:
    rows = [("p1", "매일 09:00~18:00"), ("p1", "매일 09:00~18:00"), ("p1", "매일 09:00~18:00")]
    single, multi = group_raw_texts(rows)
    assert single == {"p1": "매일 09:00~18:00"}
    assert multi == {}


def test_ㅣ_정규화_차이만_있으면_같은_값으로_본다() -> None:
    # normalize_bar 는 `ㅣ` 를 공백으로 바꾸고 연속 공백을 줄인다 — 표기 차이만 나는
    # 요일 행들은 한 값으로 수렴해야 한다.
    rows = [("p1", "월~금 09:00~18:00 ㅣ 휴무 일요일"), ("p1", "월~금 09:00~18:00   휴무 일요일")]
    single, multi = group_raw_texts(rows)
    assert single == {"p1": "월~금 09:00~18:00 휴무 일요일"}
    assert multi == {}


def test_요일별로_다른_텍스트는_검수_큐로_간다() -> None:
    rows = [("p1", "월~금 09:00~18:00"), ("p1", "토 09:00~13:00")]
    single, multi = group_raw_texts(rows)
    assert single == {}
    assert multi == {"p1": ["월~금 09:00~18:00", "토 09:00~13:00"]}


def test_빈_텍스트는_무시된다() -> None:
    single, multi = group_raw_texts([("p1", "  "), ("p2", "매일 10:00~20:00")])
    assert single == {"p2": "매일 10:00~20:00"}
    assert "p1" not in single and "p1" not in multi


# ---------------------------------------------------------------------------
# D2 — KCISA 말단 분류 추출
# ---------------------------------------------------------------------------


def test_KCISA_라인의_말단_분류를_뽑는다() -> None:
    description = "일반동물병원\n[KCISA 원본 분류] 반려동물업 > 반려의료 > 동물병원\n[입장료] 변동"
    assert extract_leaf(description) == "동물병원"


def test_단계가_하나여도_말단으로_본다() -> None:
    assert extract_leaf("[KCISA 원본 분류] 반려동물용품") == "반려동물용품"


def test_템플릿이_없으면_None() -> None:
    assert extract_leaf("그냥 설명 문장") is None
    assert extract_leaf(None) is None
    assert extract_leaf("") is None


def test_말단이_비거나_과도하게_길면_None() -> None:
    assert extract_leaf("[KCISA 원본 분류] 반려동물업 > ") is None
    assert extract_leaf("[KCISA 원본 분류] " + "가" * 60) is None


# ---------------------------------------------------------------------------
# D4 — 신뢰도 수집
# ---------------------------------------------------------------------------


def _payload(*proposals: dict) -> dict:
    return {"proposals": list(proposals)}


def test_정책_테이블_제안만_pk별로_모은다() -> None:
    scores = collect_scores(
        [
            _payload(
                {"table": "place_pet_policies", "pk": "a", "column": "caution_note",
                 "proposed": "목줄", "reliability": 100},
                {"table": "places", "pk": "b", "column": "check_in_time",
                 "proposed": "15:00:00", "reliability": 100},
            )
        ]
    )
    assert set(scores) == {"a"}
    assert scores["a"][0] == 100


def test_정규식과_LLM이_섞이면_낮은_신뢰도를_쓴다() -> None:
    scores = collect_scores(
        [
            _payload({"table": "place_pet_policies", "pk": "a", "column": "max_weight_kg",
                      "proposed": 10, "reliability": 100}),
            _payload({"table": "place_pet_policies", "pk": "a", "column": "caution_note",
                      "proposed": "주의", "reliability": 70}),
        ]
    )
    assert scores["a"][0] == 70
    assert ("caution_note", "주의") in scores["a"][1]

def test_화이트리스트_밖_컬럼은_즉시_거부된다() -> None:
    import pytest

    with pytest.raises(SystemExit, match="허용되지 않은 대상"):
        collect_scores(
            [_payload({"table": "place_pet_policies", "pk": "a",
                       "column": "notes; DROP TABLE users", "proposed": "x",
                       "reliability": 100})]
        )


# ---------------------------------------------------------------------------
# apply_place_batch 신뢰도 기록 (통합) — 코드 리뷰 지적 보강
# ---------------------------------------------------------------------------


def test_정책_반영은_신뢰도를_최저값으로_기록한다(db: Session, monkeypatch) -> None:
    """정규식(100) 반영 뒤 LLM(70)이 같은 행의 다른 컬럼을 채우면 70 이 남아야 한다."""
    import json

    from app.db.models import Place, PlacePetPolicy
    from app.db.models.enums import DataProvider
    from scripts import apply_place_batch as apb

    place = Place(
        id=uuid.uuid4(), name="신뢰도 테스트", category="etc", latitude=33.4, longitude=126.5
    )
    db.add(place)
    db.flush()
    policy = PlacePetPolicy(id=uuid.uuid4(), place_id=place.id, source=DataProvider.KCISA)
    db.add(policy)
    db.flush()

    def run(reliability: int, column: str, value, min_rel: int, tmp_path) -> None:
        staging = tmp_path / f"staging-{reliability}-{column}.json"
        staging.write_text(
            json.dumps({"proposals": [{
                "table": "place_pet_policies", "pk": str(policy.id), "column": column,
                "current": None, "proposed": value, "reliability": reliability,
                "method": "test", "evidence": "",
            }]}, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(apb, "SessionLocal", lambda: db)
        monkeypatch.setattr(db, "commit", db.flush)  # 트랜잭션 롤백 유지
        monkeypatch.setattr(db, "close", lambda: None)
        monkeypatch.setattr(
            "sys.argv",
            ["apply_place_batch", "--in", str(staging), "--apply",
             "--min-reliability", str(min_rel)],
        )
        apb.main()

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        run(100, "muzzle_required", True, 100, Path(tmpdir))
        db.refresh(policy)
        assert policy.reliability_score == 100
        run(70, "caution_note", "주의", 70, Path(tmpdir))
        db.refresh(policy)
        assert policy.caution_note == "주의"
        assert policy.reliability_score == 70  # 최저값(min 원칙)
        assert policy.verified_at is not None
