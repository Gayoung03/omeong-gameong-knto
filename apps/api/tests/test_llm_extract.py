"""LLM 보조 추출 순수 로직 테스트 (LLM 호출 없이 — build_llm_proposals·detect_pii)."""

from scripts.llm_extract_policies import build_llm_proposals, detect_pii


class TestDetectPii:
    def test_전화번호(self):
        assert detect_pii("문의 010-1234-5678 로 연락") is True

    def test_주민번호류(self):
        assert detect_pii("생년 900101-1234567") is True

    def test_깨끗한_정책문(self):
        assert detect_pii("소형견 10kg 이하 2마리까지 동반 가능") is False

    def test_none(self):
        assert detect_pii(None) is False


class TestBuildLlmProposals:
    def test_null_컬럼만_제안_reliability_70(self):
        current = dict.fromkeys(
            ["allowed_sizes", "max_weight_kg", "max_pets_per_person",
             "muzzle_required", "food_area_allowed", "caution_note"]
        )
        result = {
            "allowed_sizes": ["small"], "max_weight_kg": 10, "max_pets_per_person": 1,
            "muzzle_required": None, "food_area_allowed": False,
            "caution_note": "체고 40cm·체중 10kg 이하 1마리",
        }
        props = build_llm_proposals("pk1", current, result, "체고 40cm 이하…")
        cols = {p["column"]: p for p in props}
        assert set(cols) == {"allowed_sizes", "max_weight_kg", "max_pets_per_person",
                             "food_area_allowed", "caution_note"}
        assert all(p["reliability"] == 70 and p["method"] == "llm" for p in props)
        assert cols["max_pets_per_person"]["proposed"] == 1
        assert cols["food_area_allowed"]["proposed"] is False

    def test_이미_값_있는_컬럼은_건너뜀(self):
        current = {"allowed_sizes": ["large"], "max_weight_kg": None,
                   "max_pets_per_person": None, "muzzle_required": None,
                   "food_area_allowed": None, "caution_note": None}
        result = {"allowed_sizes": ["small"], "max_weight_kg": 5}
        props = build_llm_proposals("pk2", current, result, "…")
        cols = {p["column"] for p in props}
        assert "allowed_sizes" not in cols  # 이미 값 있음 → 재적재 안 함
        assert "max_weight_kg" in cols

    def test_caution_note_150자_절단(self):
        current = dict.fromkeys(
            ["allowed_sizes", "max_weight_kg", "max_pets_per_person",
             "muzzle_required", "food_area_allowed", "caution_note"]
        )
        result = {"caution_note": "가" * 200}
        [p] = build_llm_proposals("pk3", current, result, "…")
        assert len(p["proposed"]) == 150

    def test_null과_빈리스트는_제안_안_함(self):
        current = dict.fromkeys(
            ["allowed_sizes", "max_weight_kg", "max_pets_per_person",
             "muzzle_required", "food_area_allowed", "caution_note"]
        )
        result = {"allowed_sizes": [], "max_weight_kg": None}
        assert build_llm_proposals("pk4", current, result, "…") == []
