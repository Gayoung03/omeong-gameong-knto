"""notes·영업시간 정규식 파서 단위 테스트 (DB 불필요 — 순수 로직).

케이스는 리허설(프로덕션 덤프) 실 데이터 샘플에서 가져왔다.
"""

from datetime import time
from decimal import Decimal

from scripts.notes_parsing import (
    extract_food_area_allowed,
    extract_max_pets,
    extract_max_weight_kg,
    extract_muzzle_required,
    extract_sizes,
    normalize_bar,
    parse_check_in_out,
    parse_hours,
    parse_kcisa_kv,
    split_blocks,
)


class TestNormalizeBar:
    def test_ㅣ_는_공백으로(self):
        assert normalize_bar("휴관ㅣ매월 4째주") == "휴관 매월 4째주"

    def test_연속_공백_축약(self):
        assert normalize_bar("입실시간 ㅣ  14:00") == "입실시간 14:00"

    def test_none(self):
        assert normalize_bar(None) is None


class TestSplitBlocks:
    def test_이중_시점_분리(self):
        notes = (
            "[기존 정책]\n소형견·중형견\n반려동물을 위한 공간ㅣ 76\n"
            "[KCISA]\n반려동물 동반 가능정보: Y\n입장 가능 동물 크기: 모두 가능"
        )
        kcisa, legacy = split_blocks(notes)
        assert "반려동물 동반 가능정보: Y" in kcisa
        assert "[KCISA]" not in kcisa
        assert "소형견·중형견" in legacy

    def test_마크_없으면_원문_그대로(self):
        assert split_blocks("소형견 10kg 미만") == ("소형견 10kg 미만", None)

    def test_none(self):
        assert split_blocks(None) == (None, None)


class TestParseKcisaKv:
    def test_kv_파싱(self):
        block = (
            "반려동물 동반 가능정보: Y\n입장 가능 동물 크기: 모두 가능\n"
            "애견 동반 추가 요금: 없음"
        )
        kv = parse_kcisa_kv(block)
        assert kv["반려동물 동반 가능정보"] == "Y"
        assert kv["입장 가능 동물 크기"] == "모두 가능"
        assert kv["애견 동반 추가 요금"] == "없음"

    def test_빈_블록(self):
        assert parse_kcisa_kv(None) == {}


class TestExtractSizes:
    def test_모두_가능(self):
        assert extract_sizes("입장 가능 동물 크기: 모두 가능") == ["small", "medium", "large"]

    def test_소형견만(self):
        assert extract_sizes("소형견 10kg 미만") == ["small"]

    def test_세_크기_모두_언급(self):
        assert extract_sizes("소형견·중형견·대형견 2M 이내") == ["small", "medium", "large"]

    def test_없음(self):
        assert extract_sizes("반려동물 제한사항: 제한사항 없음") is None


class TestExtractMaxWeight:
    def test_미만(self):
        assert extract_max_weight_kg("소형견 10kg 미만") == Decimal("10")

    def test_이하(self):
        assert extract_max_weight_kg("소형견 15kg 이하") == Decimal("15")

    def test_체중_이하(self):
        assert extract_max_weight_kg("체고 40cm 이하, 체중 10kg 이하") == Decimal("10")

    def test_이상은_상한_아님(self):
        # "5kg 이상 탑승 문의" 는 하한이라 max_weight 가 아니다.
        assert extract_max_weight_kg("5kg 이상 탑승 문의") is None


class TestExtractMaxPets:
    def test_N마리(self):
        assert extract_max_pets("최대 3마리까지 입장 가능") == 3

    def test_투숙_1마리(self):
        assert extract_max_pets("생후 3개월이 지난 반려견 1마리까지 투숙 가능") == 1

    def test_깨진_표기_2M(self):
        # 'N마리' 의 깨진 표기 '2M 이내'.
        assert extract_max_pets("소형견·중형견·대형견 2M 이내") == 2

    def test_없음(self):
        assert extract_max_pets("소형견 10kg 미만") is None


class TestExtractMuzzleAndFood:
    def test_입마개(self):
        assert extract_muzzle_required("입마개 착용 필수") is True

    def test_입마개_미언급은_None(self):
        assert extract_muzzle_required("소형견 10kg 미만") is None

    def test_식음료_공간_불가(self):
        assert extract_food_area_allowed("식음료 공간 반려동물 동반 입장 불가") is False

    def test_식음료_미언급은_None(self):
        assert extract_food_area_allowed("소형견 10kg 미만") is None


class TestParseHours:
    def test_영업시간_첫구간(self):
        raw = "09:00-18:00 (17:00 입장마감 ) (휴관ㅣ매월 4째주 월요일)"
        assert parse_hours(raw) == (time(9, 0), time(18, 0))

    def test_시각_없으면_None(self):
        assert parse_hours("연중무휴") == (None, None)


class TestParseCheckInOut:
    def test_입실_퇴실(self):
        raw = "입실시간 ㅣ 14:00\n퇴실시간 ㅣ 12:00"
        assert parse_check_in_out(raw) == (time(14, 0), time(12, 0))

    def test_체크인_체크아웃_변형(self):
        assert parse_check_in_out("체크인 15:00 체크아웃 11:00") == (time(15, 0), time(11, 0))

    def test_없으면_None(self):
        assert parse_check_in_out("09:00-18:00") == (None, None)
