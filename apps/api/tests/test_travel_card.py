"""여행기록 카드 파이프라인 — 모델을 부르지 않는 부분만 검증한다.

vision·caption·image_edit 의 실제 호출은 여기서 다루지 않는다(돈이 들고 비결정적이다).
대신 **호출 결과를 어떻게 해석하는가**를 잠근다. 특히 안전 판정은 실수하면 조용히
검증 없이 통과하는 종류의 버그라, 문자열 하나까지 고정해 둔다.
"""

import struct

import pytest

from app.integrations.llm.travel_card import config, image_edit, image_io, prompts
from app.integrations.llm.travel_card.types import CardText, ImageInput, PhotoKind, WritingStyle
from app.integrations.llm.travel_card.vision import parse_analysis

# ---------------------------------------------------------------------------
# 안전 판정 — 애매하면 전부 차단이어야 한다
# ---------------------------------------------------------------------------


def test_safe_only_when_boolean_true():
    raw = '{"kind":"pet_solo","items":["흰 강아지"],"safe":true,"flags":[]}'
    analysis = parse_analysis(raw)
    assert analysis.safe is True
    assert analysis.kind is PhotoKind.PET_SOLO
    assert analysis.items == ["흰 강아지"]


@pytest.mark.parametrize(
    ("label", "raw"),
    [
        ("깨진 JSON", '{"kind":"pet_solo", "safe": tru'),
        ("빈 응답", ""),
        ("JSON 배열", "[]"),
        ("코드펜스", '```json\n{"safe":true}\n```'),
        ("문자열 true", '{"kind":"pet_solo","items":[],"safe":"true"}'),
        ("safe 누락", '{"kind":"pet_solo","items":[]}'),
        ("safe null", '{"kind":"pet_solo","items":[],"safe":null}'),
        ("safe 정수 1", '{"kind":"pet_solo","items":[],"safe":1}'),
        ("safe false", '{"kind":"food","items":[],"safe":false,"flags":["violence"]}'),
    ],
)
def test_ambiguous_analysis_is_blocked(label, raw):
    """파싱 실패도 차단이다. 통과가 기본값이면 판정 자체가 없는 것과 같다."""
    assert parse_analysis(raw).safe is False, label


def test_blocked_result_always_has_a_flag():
    """사유가 비어 있으면 로그에서 원인을 못 찾는다."""
    assert parse_analysis('{"safe":false}').flags
    assert parse_analysis("깨짐").flags


def test_unknown_kind_falls_back_to_other():
    assert parse_analysis('{"kind":"셀카","items":[],"safe":true}').kind is PhotoKind.OTHER


# ---------------------------------------------------------------------------
# 분류
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (PhotoKind.PET_SOLO, True),
        (PhotoKind.PET_WITH_HUMAN, True),
        (PhotoKind.PET_WITH_PET, True),
        (PhotoKind.SCENERY, False),
        (PhotoKind.FOOD, False),
        (PhotoKind.OBJECT, False),
        (PhotoKind.OTHER, False),
    ],
)
def test_has_pet(kind, expected):
    """강아지 일기의 화자 시점을 가르는 값이라 정확해야 한다."""
    assert kind.has_pet is expected


# ---------------------------------------------------------------------------
# 출력 크기 — 비율은 프롬프트가 아니라 코드가 지킨다
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [
        (4032, 3024, "1536x1024"),
        (1920, 1080, "1536x1024"),
        (3024, 4032, "1024x1536"),
        (1080, 1920, "1024x1536"),
        (1000, 1000, "1024x1024"),
    ],
)
def test_pick_size_follows_orientation(width, height, expected):
    assert image_edit.pick_size(ImageInput(b"", "image/jpeg", width, height)) == expected


# ---------------------------------------------------------------------------
# 이미지 읽기 — 확장자가 아니라 내용을 본다
# ---------------------------------------------------------------------------


def _png(width: int, height: int) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        + b"\x00" * 4
    )


def test_load_png():
    image = image_io.load_image(_png(800, 600))
    assert (image.mime_type, image.width, image.height) == ("image/png", 800, 600)


@pytest.mark.parametrize(
    ("label", "data"),
    [
        ("빈 파일", b""),
        ("GIF", b"GIF89a" + b"\x00" * 40),
        ("HEIC 흉내", b"\x00\x00\x00\x18ftypheic" + b"\x00" * 40),
        ("텍스트", "그냥 글자".encode()),
    ],
)
def test_unreadable_images_are_rejected(label, data):
    with pytest.raises(image_io.UnreadableImage):
        image_io.load_image(data)


def test_oversized_image_is_rejected():
    with pytest.raises(image_io.UnreadableImage):
        image_io.load_image(b"\xff\xd8\xff" + b"\x00" * (11 * 1024 * 1024))


# ---------------------------------------------------------------------------
# 프롬프트 조립 — 호출이 없으니 전부 검증할 수 있다
# ---------------------------------------------------------------------------


def _text(title: str = "오늘의 제주", memos: list[str] | None = None) -> CardText:
    return CardText(title=title, memos=memos if memos is not None else ["바당이 곱나"])


def test_guard_is_always_present():
    """한글 깨짐을 막는 문장이 빠지면 이 기능의 최대 난제가 무방비가 된다."""
    prompt = prompts.build(PhotoKind.PET_SOLO, WritingStyle.JEJU_DIALECT, _text())
    assert "온전한 음절" in prompt
    assert "맛있ㅓ" in prompt  # 실패 예시를 그대로 보여줘야 모델이 알아듣는다
    assert "통째로 빼고" in prompt
    assert "원본 사진을 다시 그리지 마" in prompt


def test_memos_carry_no_numbering():
    """번호를 붙여 넘기면 모델이 그 번호까지 글자로 그린다(2026-09-09 실측)."""
    memos = ["집사가 백 장 찍었댕", "하늘이 예쁘댕", "그늘에서 기다렸개"]
    prompt = prompts.build(PhotoKind.SCENERY, WritingStyle.DOG_DIARY, _text(memos=memos))
    for index, memo in enumerate(memos, 1):
        assert memo in prompt
        assert f"{index}. {memo}" not in prompt
    assert "번호나 불릿을 그리지 마" in prompt


def test_title_is_separate_from_memos():
    prompt = prompts.build(
        PhotoKind.SCENERY, WritingStyle.DOG_DIARY, _text("몽이의 바다", ["기다렸개"])
    )
    assert "[제목 — 크고 굵게 한 번만]" in prompt
    assert "몽이의 바다" in prompt


def test_scenery_forbids_drawing_animals():
    """풍경 사진에 없는 강아지를 그려 넣는 것이 최악의 실패다."""
    prompt = prompts.build(PhotoKind.SCENERY, WritingStyle.DOG_DIARY, _text(memos=["기다렸개"]))
    assert "동물을 그려 넣지 마" in prompt


def test_styles_differ_in_pen_and_decoration():
    jeju = prompts.build(PhotoKind.PET_SOLO, WritingStyle.JEJU_DIALECT, _text())
    dog = prompts.build(PhotoKind.PET_SOLO, WritingStyle.DOG_DIARY, _text())
    assert jeju != dog
    assert "감귤" in jeju and "발바닥" not in jeju
    assert "발바닥" in dog and "감귤" not in dog


def test_memo_range_is_not_inverted():
    """MIN > MAX 면 프롬프트에 "메모 8~6개" 같은 범위가 나간다(2026-09-09 실측).

    둘 중 하나만 환경변수로 덮었을 때 실제로 겪은 일이다. 모델은 앞의 숫자를 따라
    8개를 만들고, 코드가 뒤 2개를 조용히 잘라냈다 — 6개로 짜인 글이 아니었다.
    """
    assert config.MIN_MEMOS <= config.MAX_MEMOS
    assert config.MAX_MEMOS >= 3  # _coerce_memos 의 하한과 어긋나면 항상 실패한다


def test_place_and_date_only_when_given():
    without = prompts.build(PhotoKind.FOOD, WritingStyle.JEJU_DIALECT, _text())
    assert "상단 여백" not in without

    with_place = prompts.build(
        PhotoKind.FOOD,
        WritingStyle.JEJU_DIALECT,
        _text(),
        place_name="협재해수욕장",
        date_text="2026.09.08",
    )
    assert "협재해수욕장" in with_place and "2026.09.08" in with_place
