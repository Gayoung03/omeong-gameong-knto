"""여행기록 카드 파이프라인 — 모델을 부르지 않는 부분만 검증한다.

vision·caption·image_edit 의 실제 호출은 여기서 다루지 않는다(돈이 들고 비결정적이다).
대신 **호출 결과를 어떻게 해석하는가**를 잠근다. 특히 안전 판정은 실수하면 조용히
검증 없이 통과하는 종류의 버그라, 문자열 하나까지 고정해 둔다.
"""

import io
import struct

import pytest
from PIL import Image, ImageDraw

from app.integrations.llm.travel_card import (
    caption,
    card_render,
    config,
    image_edit,
    image_io,
    prompts,
    vision,
)
from app.integrations.llm.travel_card.types import (
    CardText,
    ImageInput,
    Memo,
    PhotoKind,
    WritingStyle,
)
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
# 머리 칸 — 프롬프트로 네 번 말해도 안 되던 것을 좌표로 옮겼다
# ---------------------------------------------------------------------------


def test_grid_has_nine_named_zones():
    """칸 이름이 바뀌면 프롬프트 설명과 파서가 조용히 어긋난다."""
    assert len(vision.ZONES) == 9
    assert "왼쪽-중간" in vision.ZONES
    assert "오른쪽-아래" in vision.ZONES


def test_head_zones_are_cleaned_up():
    """모델이 준 칸 이름을 그대로 믿지 않는다.

    모르는 이름은 버리고, 중복은 한 번만 세고, **3칸까지만** 받는다.
    9칸을 다 막으면 글씨 놓을 곳이 없어져 배치가 통째로 무너진다.
    """
    raw = (
        '{"kind":"scenery","items":[],"safe":true,'
        '"headZones":["왼쪽-중간","없는칸","가운데-중간","왼쪽-중간","오른쪽-위","왼쪽-아래"]}'
    )

    assert parse_analysis(raw).head_zones == ["왼쪽-중간", "가운데-중간", "오른쪽-위"]


@pytest.mark.parametrize("value", ['"왼쪽-중간"', "null", "123", "{}"])
def test_head_zones_survive_a_wrong_shape(value):
    """리스트가 아니면 빈 목록이다 — 머리 칸 하나 때문에 카드를 못 만들면 안 된다."""
    raw = f'{{"kind":"scenery","items":[],"safe":true,"headZones":{value}}}'

    assert parse_analysis(raw).head_zones == []


def test_back_of_a_head_counts_too():
    """뒷모습이라고 빼면 금지 구역이 통째로 안 붙는다(2026-09-15 실측).

    처음엔 vision 에게 "얼굴"을 물었고 `뒷모습이면 적지 마` 라고까지 써 뒀다.
    그런데 실제 사진이 **자전거 탄 뒷모습**이라 빈 배열이 왔고, 블록이 프롬프트에
    없는 채로 카드가 나왔다 — 붙였다고 생각한 장치가 한 번도 안 돈 것이다.
    "머리" 로 고친 뒤 같은 사진에서 두 사람을 다 잡았다.
    """
    assert "뒷모습" in vision.SYSTEM_PROMPT
    assert "얼굴이 안 보이면 적지 않는다" not in vision.SYSTEM_PROMPT


def test_head_zones_become_a_no_go_block():
    """`vision` 이 찾은 칸이 프롬프트에 좌표로 박힌다."""
    prompt = prompts.build(
        PhotoKind.SCENERY,
        WritingStyle.JEJU_DIALECT,
        _text(),
        loose=True,
        head_zones=["왼쪽-중간", "가운데-중간"],
    )

    assert "비워둘 자리" in prompt
    assert "· 왼쪽-중간" in prompt
    assert "· 가운데-중간" in prompt
    # 몸통은 괜찮다 — 전부 막으면 놓을 곳이 없어진다(사장님 기준, 09-14).
    assert "머리만 피하면 된다" in prompt


def test_no_go_block_disappears_without_heads():
    """가릴 머리가 없는데 금지 구역을 말하면 규칙만 하나 늘어난다."""
    prompt = prompts.build(PhotoKind.FOOD, WritingStyle.DOG_DIARY, _text(), loose=True)

    assert "비워둘 자리" not in prompt


def test_scenery_photo_can_still_carry_heads():
    """사람만 있고 반려동물이 없는 사진은 `scenery` 로 분류된다(09-14 실측).

    분류 체계에 "사람만" 칸이 없어 `pet_with_human` 힌트에 걸리지 않는다.
    머리 칸은 **분류와 무관하게** 동작해야 그 구멍이 메워진다.
    """
    prompt = prompts.build(
        PhotoKind.SCENERY, WritingStyle.JEJU_DIALECT, _text(), head_zones=["왼쪽-중간"]
    )

    assert "비워둘 자리" in prompt


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


def _jpeg_with_orientation(width: int, height: int, orientation: int) -> bytes:
    """EXIF Orientation 을 가진 최소 JPEG. 실제 휴대폰 사진의 모양을 흉내 낸다."""
    tiff = (
        b"II\x2a\x00"
        + struct.pack("<I", 8)
        + struct.pack("<H", 1)
        + struct.pack("<HHI", 0x0112, 3, 1)
        + struct.pack("<HH", orientation, 0)
        + struct.pack("<I", 0)
    )
    exif = b"Exif\x00\x00" + tiff
    app1 = b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif
    sof = b"\xff\xc0" + struct.pack(">H", 17) + b"\x08" + struct.pack(">HH", height, width)
    # SOI 다음에 바로 APP1 이 온다. 사이에 0xFF 를 하나 더 넣으면 파서가 어긋난다.
    return b"\xff\xd8" + app1 + sof + b"\x00" * 8


def test_exif_rotated_photo_reports_display_size():
    """세로로 찍은 사진은 파일 안에서 가로 픽셀로 들어 있다(2026-09-12 실측).

    이 값을 무시하면 세로 사진에 가로 캔버스를 요청하게 되고, 모델이 장면을 다시
    짜면서 사람 얼굴까지 바뀐다. 실제로 그 사고가 났다.
    """
    upright = image_io.load_image(_jpeg_with_orientation(4032, 3024, 1))
    assert (upright.width, upright.height) == (4032, 3024)

    rotated = image_io.load_image(_jpeg_with_orientation(4032, 3024, 6))
    assert (rotated.width, rotated.height) == (3024, 4032)
    assert image_edit.pick_size(rotated) == "1024x1536"


def test_oversized_image_is_rejected():
    with pytest.raises(image_io.UnreadableImage):
        image_io.load_image(b"\xff\xd8\xff" + b"\x00" * (11 * 1024 * 1024))


# ---------------------------------------------------------------------------
# 프롬프트 조립 — 호출이 없으니 전부 검증할 수 있다
# ---------------------------------------------------------------------------


def _text(
    title: str = "오늘의 제주",
    memos: list[str] | None = None,
    targets: list[str | None] | None = None,
) -> CardText:
    lines = memos if memos is not None else ["바당이 곱나"]
    marks = targets if targets is not None else [None] * len(lines)
    return CardText(title=title, memos=[Memo(t, g) for t, g in zip(lines, marks, strict=True)])


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


def test_arrow_is_removed_with_its_memo():
    """메모를 빼면서 화살표만 남기면 허공을 가리키는 선이 생긴다(2026-09-12 실측).

    "자신 없으면 메모를 빼라" 는 가드의 부작용이었다. 빼라고만 했지 딸린 화살표까지
    빼라고는 안 해서, 가리킬 글이 없는 점선이 사진에 남았다.
    """
    prompt = prompts.build(PhotoKind.SCENERY, WritingStyle.JEJU_DIALECT, _text())
    assert "화살표와 점선도 반드시 함께 뺀다" in prompt


def test_memo_placement_follows_content():
    """하늘 이야기가 잔디 위에 놓이면 읽는 사람이 헷갈린다(2026-09-12 실측)."""
    prompt = prompts.build(PhotoKind.PET_SOLO, WritingStyle.DOG_DIARY, _text())
    assert "말하는 대상 가까이에 놓는다" in prompt
    assert "하늘" in prompt and "아래쪽" in prompt


def test_loose_also_says_where_each_memo_goes():
    """`--loose` 에도 내용-자리 대응이 있어야 한다(2026-09-14 실측).

    그 전 loose 는 `여백에 고르게` 만 말했다. 그래서 하늘 이야기("푸른 하늘이 참
    멋지우다")가 갈 곳을 모른 채 빈 곳을 찾다 **화면 한가운데 사람 머리 위**에
    놓였다.

    얼굴을 가리지 말라는 줄은 loose 에도 이미 있었고 그래도 어겼다. 고친 것은
    금지를 세게 한 쪽이 아니라 **갈 곳을 알려준 쪽**이다.

    09-10 문장(`여백을 찾아 배치해줘`)은 그대로 두고 조건만 달았다 —
    `test_loose_layout_restores_the_short_09_10_wording` 이 지키는 선이다.
    """
    prompt = prompts.build(
        PhotoKind.PET_WITH_HUMAN, WritingStyle.JEJU_DIALECT, _text(), loose=True
    )

    assert "그 메모가 말하는 것과 가까운 여백" in prompt
    assert "하늘·구름 이야기" in prompt
    # 얼굴 금지는 그대로 남아 있어야 한다 — 대체가 아니라 추가다.
    assert "얼굴은 글씨나 화살표로 가리지 마" in prompt


def test_loose_stays_shorter_than_strict():
    """loose 의 존재 이유는 짧다는 것이다 — 규칙을 더하다 strict 가 되면 의미가 없다.

    2026-09-13 에 배운 것: 규칙 하나하나는 실제 문제를 고쳤지만 **누적이 자유를
    없앴다.** 09-14 에 세 줄을 더하면서 이 선을 테스트로 박아 둔다.
    """
    text = _text()
    loose = prompts.build(PhotoKind.PET_SOLO, WritingStyle.DOG_DIARY, text, loose=True)
    strict = prompts.build(PhotoKind.PET_SOLO, WritingStyle.DOG_DIARY, text)

    assert len(loose.splitlines()) < len(strict.splitlines())
    # 화살표 계약(strict 11줄)은 loose 로 넘어오지 않는다.
    assert "화살표 — 장식이 아니다" not in loose


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


# ---------------------------------------------------------------------------
# card_render — 원본은 그대로 두고 손글씨만 옮겨 얹는다
# ---------------------------------------------------------------------------


def _photo(size: tuple[int, int], color: tuple[int, int, int]) -> ImageInput:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "JPEG", quality=95)
    data = buffer.getvalue()
    return ImageInput(data=data, mime_type="image/jpeg", width=size[0], height=size[1])


def _card(size: tuple[int, int], background: tuple[int, int, int], *, stroke: bool) -> bytes:
    """생성 카드를 흉내 낸다. `stroke` 가 참이면 얇은 흰 획을 하나 긋는다."""
    image = Image.new("RGB", size, background)
    if stroke:
        ImageDraw.Draw(image).line(
            [(size[0] // 4, size[1] // 2), (size[0] * 3 // 4, size[1] // 2)],
            fill=(255, 255, 255),
            width=12,
        )
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def _composed(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png)).convert("RGB")


def test_final_card_keeps_original_aspect_ratio():
    """생성 캔버스는 1024/1536 세 종류뿐이라 원본 비율과 어긋난다. 최종은 원본을 따라야 한다."""
    color = (90, 140, 200)
    original = _photo((4000, 3000), color)
    out = _composed(card_render.compose(original, _card((1536, 1024), color, stroke=False)))

    assert max(out.size) == card_render.LONG_EDGE
    assert out.width / out.height == pytest.approx(4000 / 3000, abs=0.01)


def test_portrait_photo_stays_portrait():
    color = (90, 140, 200)
    original = _photo((3000, 4000), color)
    out = _composed(card_render.compose(original, _card((1024, 1536), color, stroke=False)))

    assert out.height > out.width


def test_photo_without_handwriting_is_left_untouched():
    """획이 없으면 원본이 한 픽셀도 바뀌지 않아야 한다 — 얼굴이 지켜지는 근거가 이것이다."""
    color = (90, 140, 200)
    original = _photo((1200, 900), color)
    out = _composed(card_render.compose(original, _card((1200, 900), color, stroke=False)))

    assert out.getpixel((out.width // 2, out.height // 2)) == pytest.approx(color, abs=3)
    assert out.getpixel((10, 10)) == pytest.approx(color, abs=3)


def test_handwriting_is_carried_over_but_only_where_it_was():
    color = (90, 140, 200)
    original = _photo((1200, 900), color)
    out = _composed(card_render.compose(original, _card((1200, 900), color, stroke=True)))

    on_stroke = out.getpixel((out.width // 2, out.height // 2))
    far_away = out.getpixel((20, 20))
    assert min(on_stroke) > 220, f"획이 옮겨지지 않았다: {on_stroke}"
    assert far_away == pytest.approx(color, abs=3), f"획 밖이 바뀌었다: {far_away}"


def test_stroke_gets_a_shadow_so_it_reads_on_bright_backgrounds():
    """흰 글씨가 밝은 하늘에 얹히면 그림자 없이는 안 보인다."""
    bright = (245, 245, 245)
    original = _photo((1200, 900), bright)
    out = _composed(card_render.compose(original, _card((1200, 900), (120, 120, 120), stroke=True)))

    beside = out.getpixel((out.width // 2, out.height // 2 + 9))
    # 진하면 글씨 둘레가 지저분해지므로 세기가 아니라 **있고 없음**을 잠근다.
    assert max(beside) < max(bright) - 25, f"획 둘레에 그림자가 없다: {beside}"
    assert max(beside) > 90, f"그림자가 너무 진해 글씨 둘레가 지저분하다: {beside}"


def test_bright_thin_things_already_in_the_photo_are_not_mistaken_for_handwriting():
    """나뭇잎 틈 하늘·흰 운동화·흰 털이 손글씨로 딸려 오던 버그(2026-09-12).

    원본에도 있던 것은 손글씨가 아니다. 잘못 치면 그 자리에 흰 덩어리와 그림자가 얹힌다.
    """
    blue = (90, 140, 200)
    decoy_y = 300

    def _with_decoy(color: tuple[int, int, int], brightness: int) -> Image.Image:
        image = Image.new("RGB", (1200, 900), color)
        ImageDraw.Draw(image).line(
            [(200, decoy_y), (1000, decoy_y)], fill=(brightness,) * 3, width=6
        )
        return image

    buffer = io.BytesIO()
    _with_decoy(blue, 240).save(buffer, "JPEG", quality=95)
    original = ImageInput(
        data=buffer.getvalue(), mime_type="image/jpeg", width=1200, height=900
    )
    # 생성물은 같은 것을 다시 그리므로 조금 더 밝게 나온다 — 그래도 손글씨가 아니다.
    card = io.BytesIO()
    _with_decoy(blue, 252).save(card, "PNG")

    out = _composed(card_render.compose(original, card.getvalue()))
    scale = out.height / 900
    beside = out.getpixel((out.width // 2, round(decoy_y * scale) + 12))

    assert beside == pytest.approx(blue, abs=12), f"원본에 있던 것에 그림자가 깔렸다: {beside}"


# ---------------------------------------------------------------------------
# 손글씨 레이어 모드 — 어느 픽셀이 손글씨인지 추측하지 않는다
# ---------------------------------------------------------------------------


def _plate(size: tuple[int, int], *, blank: bool = False) -> bytes:
    """검은 바탕에 흰 획 하나. 이미지 모델이 돌려주기를 기대하는 모양이다."""
    image = Image.new("RGB", size, (0, 0, 0))
    if not blank:
        ImageDraw.Draw(image).line(
            [(size[0] // 4, size[1] // 2), (size[0] * 3 // 4, size[1] // 2)],
            fill=(255, 255, 255),
            width=12,
        )
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_plate_carries_handwriting_onto_untouched_white_fur():
    """흰 털·흰 운동화가 딸려 오던 자리다. 레이어에는 애초에 그것이 없다."""
    white_ish = (246, 246, 244)
    original = _photo((1200, 900), white_ish)
    out = _composed(card_render.compose_from_plate(original, _plate((1200, 900))))

    on_stroke = out.getpixel((out.width // 2, out.height // 2))
    far_away = out.getpixel((20, 20))
    assert min(on_stroke) > 220, f"획이 옮겨지지 않았다: {on_stroke}"
    assert far_away == pytest.approx(white_ish, abs=3), f"흰 배경이 바뀌었다: {far_away}"


def test_plate_that_is_actually_a_photo_is_rejected():
    """모델이 '배경을 검게' 를 무시하면 눈으로 보기 전에 걸려야 한다."""
    original = _photo((1200, 900), (90, 140, 200))
    not_a_plate = _card((1200, 900), (90, 140, 200), stroke=True)

    with pytest.raises(card_render.RenderError):
        card_render.compose_from_plate(original, not_a_plate)


def test_plate_prompt_demands_black_and_drops_the_photo_preserving_rules():
    text = _text(memos=["푸른 잔디에서 뛰어놀았댕"])
    plate = prompts.build(PhotoKind.PET_SOLO, WritingStyle.DOG_DIARY, text, ink_plate=True)
    photo = prompts.build(PhotoKind.PET_SOLO, WritingStyle.DOG_DIARY, text)

    assert "검은 배경" in plate and "완전한 검정" in plate
    # 사진을 그대로 두라는 지시는 레이어 모드에서 정반대다. 남아 있으면 모델이 헷갈린다.
    assert "원본 사진을 다시 그리지 마" not in plate
    assert "원본 사진을 다시 그리지 마" in photo
    # 메모 내용과 한글 가드는 두 모드가 같아야 한다.
    assert text.memos[0].text in plate
    assert "온전한 음절 블록" in plate


# ---------------------------------------------------------------------------
# 화살표 — 허공을 가리키던 문제(2026-09-12)
# ---------------------------------------------------------------------------


def test_memo_without_a_target_is_marked_as_no_arrow():
    """날씨·기분에는 가리킬 지점이 없다. 화살표를 달면 끝이 빈 곳에 떨어진다."""
    text = _text(
        memos=["입을 벌리고 신나게 놀았댕", "햇볕이 폭싹 쏟아진 날이우다"],
        targets=["입을 벌린 흰 강아지", None],
    )
    prompt = prompts.build(PhotoKind.PET_SOLO, WritingStyle.DOG_DIARY, text, ink_plate=True)

    assert "· 입을 벌리고 신나게 놀았댕   (가리킬 것: 입을 벌린 흰 강아지)" in prompt
    assert "· 햇볕이 폭싹 쏟아진 날이우다   (화살표 없음)" in prompt


def test_arrow_contract_states_both_ends():
    """'시선을 유도해줘' 한 줄로는 시작도 끝도 정해지지 않는다 — 그래서 흩뿌려졌다."""
    prompt = prompts.build(PhotoKind.SCENERY, WritingStyle.JEJU_DIALECT, _text())

    assert "허공에서 시작하면 안 된다" in prompt
    assert "대상을 지나쳐 빈 곳으로 빠지면 안 된다" in prompt
    assert "절대 화살표를 그리지 마라" in prompt
    # 괄호 안 지시가 글자로 그려지면 카드가 망가진다.
    assert "화살표 지시일 뿐 글자가 아니다" in prompt


def test_invented_or_duplicate_targets_are_dropped():
    """사진에 없는 대상을 가리키는 화살표는 아무것도 가리키지 못한다."""
    items = ["입을 벌린 흰 강아지", "초록 잔디밭"]
    payload = {
        "memos": [
            {"text": "입을 벌리고 신나게 놀았댕", "target": "입을 벌린 흰 강아지"},
            {"text": "푸른 잔디 위에 서 있었댕", "target": "존재하지 않는 무지개"},
            {"text": "나도 잔디가 좋댕", "target": "입을 벌린 흰 강아지"},
            {"text": "햇빛이 좋았댕", "target": None},
        ]
    }
    memos = caption._coerce_memos(payload, items)

    assert [m.target for m in memos] == ["입을 벌린 흰 강아지", None, None, None]


def test_plain_string_memos_still_load():
    """모델이 옛 모양(문자열 배열)으로 답해도 카드가 나가야 한다."""
    memos = caption._coerce_memos({"memos": ["바당이 곱수다"]}, ["바당"])

    assert [m.text for m in memos] == ["바당이 곱수다"]
    assert memos[0].target is None


# ---------------------------------------------------------------------------
# 제목 — 명사로 끝나는 제목이 프롬프트를 뚫고 계속 샜다(2026-09-12)
# ---------------------------------------------------------------------------


def test_noun_titles_are_kept():
    """좋다는 평을 받은 카드의 제목이 명사로 끝났다 — 요구받은 적 없는 기준으로
    멀쩡한 제목을 걸러내고 있었다(2026-09-13).
    """
    memos = [Memo("자갈길 걸으니 기분이 좋수다")]
    for good in ("삼다수길에서 즐긴 햇살", "신창해안도로에서 즐거운 오후"):
        title, rest = caption._pick_title(good, memos)
        assert title == good
        assert rest == memos


def test_missing_or_overlong_title_is_replaced_by_the_first_memo():
    memos = [Memo("자갈길 걸으니 기분이 좋수다"), Memo("햇빛이 좋수다")]

    title, rest = caption._pick_title("", memos)
    assert title == "자갈길 걸으니 기분이 좋수다"
    assert [m.text for m in rest] == ["햇빛이 좋수다"]

    long_title, _ = caption._pick_title("스물한 글자가 넘어가는 아주아주 긴 제목이우다", memos)
    assert long_title == "자갈길 걸으니 기분이 좋수다"


def test_caption_rules_carry_the_examples_the_owner_liked():
    """참고 카드의 좋은 줄을 그대로 목표로 박아 둔다."""
    jeju = caption.build_system_prompt(WritingStyle.JEJU_DIALECT, None)
    dog = caption.build_system_prompt(WritingStyle.DOG_DIARY, "털봉")

    assert "숲속이 참 시원허우다" in jeju
    assert "파도 소리 들으니까 졸렸개" in dog
    # target 때문에 문장이 사물 나열로 흐르던 문제.
    assert "좋은 문장을 먼저 쓰고" in jeju


def test_caption_rules_ban_photo_describing_lines():
    """'보면 아는 것' 을 적는 쪽으로 도망가던 문제. 실제로 나왔던 줄을 그대로 박아둔다."""
    rules = caption.build_system_prompt(WritingStyle.JEJU_DIALECT, None)

    assert "보면 아는 것은 쓰지 마라" in rules
    assert "모자 쓴 사람과 함께 서 있었수다" in rules


def test_arrows_are_curved_dashes_not_ruler_lines():
    prompt = prompts.build(PhotoKind.SCENERY, WritingStyle.JEJU_DIALECT, _text())

    assert "완만하게 휜 곡선" in prompt
    assert "곧은 실선은 쓰지 마라" in prompt


def test_broad_backgrounds_cannot_be_arrow_targets():
    """풀·하늘·잔디는 화면에 깔려 있어 한 점을 집을 수 없다.

    "주변 풀" 을 가리키게 했더니 화살표가 사람 다리를 찍었다(2026-09-12).
    """
    rules = caption.build_system_prompt(WritingStyle.JEJU_DIALECT, None)

    assert "화면에 넓게 깔린 배경" in rules
    assert "테두리를 그릴 수 있는 하나의 물체" in rules


def test_arrowhead_must_not_land_on_a_person_when_pointing_elsewhere():
    prompt = prompts.build(PhotoKind.PET_WITH_HUMAN, WritingStyle.JEJU_DIALECT, _text())

    assert "사람이나 동물 위에 놓이면 안 된다" in prompt


def test_unreachable_targets_drop_the_arrow_instead_of_stretching_it():
    """멀리 있는 대상까지 길게 늘인 화살표가 허공에서 끝났다(2026-09-12)."""
    prompt = prompts.build(PhotoKind.PET_SOLO, WritingStyle.DOG_DIARY, _text())

    assert "메모를 놓을 자리가 없으면 그 메모의 화살표는 그리지 마라" in prompt


# ---------------------------------------------------------------------------
# 업로드 전 표준화 — 겉만 JPEG 인 휴대폰 사진(2026-09-13)
# ---------------------------------------------------------------------------


def test_extra_frames_appended_after_the_first_are_dropped():
    """MPO 는 JPEG 두 장이 한 파일에 들어 있다. 앞 4바이트가 JPEG 와 같아 형식 판정은
    통과하고 OpenAI 가 `invalid_image_file` 로 거절했다(2026-09-13, 제주_샘플_13).

    (진짜 MPO 는 APP2 마커까지 있어야 하지만, 뒤에 붙은 바이트가 떨어져 나가는지는
    이 재료로 확인할 수 있다.)
    """
    frames = []
    for color in ((90, 140, 200), (40, 40, 40)):
        buffer = io.BytesIO()
        Image.new("RGB", (1200, 900), color).save(buffer, "JPEG", quality=90)
        frames.append(buffer.getvalue())
    raw = b"".join(frames)

    ready = image_io.normalize(image_io.load_image(raw))
    reopened = Image.open(io.BytesIO(ready.data))

    assert reopened.format == "JPEG"
    assert getattr(reopened, "n_frames", 1) == 1
    assert len(ready.data) < len(raw), "뒤에 붙은 두 번째 장이 그대로 남았다"


def test_cmyk_photo_becomes_rgb():
    """스캔·인쇄용 사진이 CMYK 로 오면 이미지 API 가 받지 않는다."""
    buffer = io.BytesIO()
    Image.new("CMYK", (800, 600), (10, 20, 30, 5)).save(buffer, "JPEG")

    ready = image_io.normalize(image_io.load_image(buffer.getvalue()))

    assert Image.open(io.BytesIO(ready.data)).mode == "RGB"


def test_normalize_applies_exif_rotation_to_the_pixels():
    """표시만 남겨두면 이미지 API 가 그것을 존중하는지에 결과가 달려 있게 된다."""
    buffer = io.BytesIO()
    upright = Image.new("RGB", (1200, 900), (90, 140, 200))
    exif = upright.getexif()
    exif[0x0112] = 6  # 시계방향 90도로 돌려서 보라
    upright.save(buffer, "JPEG", exif=exif)

    ready = image_io.normalize(image_io.load_image(buffer.getvalue()))

    assert (ready.width, ready.height) == (900, 1200)
    assert Image.open(io.BytesIO(ready.data)).size == (900, 1200)


def test_normalize_shrinks_huge_photos_but_keeps_the_ratio():
    buffer = io.BytesIO()
    Image.new("RGB", (4032, 3024), (90, 140, 200)).save(buffer, "JPEG")

    ready = image_io.normalize(image_io.load_image(buffer.getvalue()))

    assert max(ready.width, ready.height) == image_io.NORMALIZED_LONG_EDGE
    assert ready.width / ready.height == pytest.approx(4032 / 3024, abs=0.01)


def test_normalize_leaves_small_photos_at_their_size():
    buffer = io.BytesIO()
    Image.new("RGB", (800, 600), (90, 140, 200)).save(buffer, "JPEG")

    ready = image_io.normalize(image_io.load_image(buffer.getvalue()))

    assert (ready.width, ready.height) == (800, 600)


# ---------------------------------------------------------------------------
# 배치 지시 두 벌 — 어느 쪽이 나은지는 눈으로 봐야 안다
# ---------------------------------------------------------------------------


def test_loose_layout_restores_the_short_09_10_wording():
    text = _text(memos=["자갈길 걸으니 좋수다"], targets=["자갈길"])
    loose = prompts.build(PhotoKind.SCENERY, WritingStyle.JEJU_DIALECT, text, loose=True)

    assert "사진의 여백을 찾아 메모를 배치해줘" in loose
    assert "부드러운 곡선 점선으로 시선을 각 아이템으로 유도해줘" in loose
    # 스무 줄짜리 계약은 통째로 빠진다 — 그게 이 모드의 요점이다.
    assert "허공에서 시작하면 안 된다" not in loose
    assert "하늘 이야기가 발밑에 놓이면" not in loose


def test_loose_layout_drops_the_target_annotations_and_their_note():
    """괄호 표기가 없는데 그 설명만 남으면 모델이 헷갈린다."""
    text = _text(memos=["자갈길 걸으니 좋수다"], targets=["자갈길"])
    loose = prompts.build(PhotoKind.SCENERY, WritingStyle.JEJU_DIALECT, text, loose=True)

    assert "· 자갈길 걸으니 좋수다" in loose
    assert "가리킬 것" not in loose
    assert "화살표 없음" not in loose


def test_both_layouts_keep_the_hangul_guard_and_the_plate_rules():
    """배치만 갈라지고 나머지는 같아야 한다 — 아니면 비교가 성립하지 않는다."""
    text = _text(memos=["자갈길 걸으니 좋수다"])
    for loose in (True, False):
        prompt = prompts.build(
            PhotoKind.SCENERY, WritingStyle.JEJU_DIALECT, text, ink_plate=True, loose=loose
        )
        assert "온전한 음절" in prompt
        assert "완전한 검정" in prompt
        assert "번호나 불릿을 그리지 마" in prompt



# ---------------------------------------------------------------------------
# 캔버스 비율 맞추기 — 글자가 가로로 늘어나던 문제(2026-09-13)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("photo", "canvas"),
    [((3024, 4032), "1024x1536"), ((4032, 3024), "1536x1024"), ((2000, 2000), "1024x1024")],
)
def test_photo_is_cropped_to_the_canvas_ratio_before_upload(photo, canvas):
    """모델이 그릴 캔버스와 사진 비율이 다르면 손글씨를 가로로 늘여 얹게 된다."""
    buffer = io.BytesIO()
    Image.new("RGB", photo, (90, 140, 200)).save(buffer, "JPEG")
    ready = image_io.normalize(image_io.load_image(buffer.getvalue()))

    fitted = image_io.fit_canvas(ready, canvas)
    width, height = (int(v) for v in canvas.split("x"))

    assert fitted.width / fitted.height == pytest.approx(width / height, abs=0.005)


def test_fitted_photo_and_plate_compose_without_stretching_the_letters():
    buffer = io.BytesIO()
    Image.new("RGB", (3024, 4032), (90, 140, 200)).save(buffer, "JPEG")
    ready = image_io.fit_canvas(
        image_io.normalize(image_io.load_image(buffer.getvalue())), "1024x1536"
    )

    out = _composed(card_render.compose_from_plate(ready, _plate((1024, 1536))))

    assert out.width / out.height == pytest.approx(1024 / 1536, abs=0.005)
