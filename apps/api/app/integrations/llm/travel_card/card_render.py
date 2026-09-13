"""단계 5 — 손글씨만 뽑아 원본 사진에 다시 얹는다.

## 왜 이 단계가 필요한가

`images.edit` 는 원본 위에 덧그리는 것이 아니라 **모든 픽셀을 새로 만든다.** 그래서
"원본을 다시 그리지 마" 라는 지시는 모델이 구조적으로 지킬 수 없다. 최대한 비슷하게
만들 뿐이다.

나무와 풀은 5% 달라져도 아무도 모르지만 **얼굴은 1%만 달라져도 알아본다.**
2026-09-12 실측에서 사람 얼굴은 물론 반려동물 얼굴까지 바뀌었다 — 눈이 커지고
얼굴이 갸름해지는 쪽으로. "더 예쁜 다른 개" 가 기록으로 남는 셈이다.

그래서 생성물을 그대로 쓰지 않고 **손글씨 레이어만 꺼내 원본에 얹는다.**
원본 사진은 한 픽셀도 건드리지 않는다.

## 어떻게 꺼내는가

손글씨는 "주변보다 밝은, 흰색에 가까운 얇은 획" 이다. 국소 대비로 잡아낼 수 있다.

    1. 생성 카드를 원본 크기로 맞춘다
    2. 흐리게 만든 자기 자신과 비교해 **주변보다 튀는 밝기**를 구하고,
       그중 흰색에 가까운 것만 남긴다
    3. **원본에도 같은 성질이 있는 자리는 뺀다** (아래)
    4. 획을 살짝 부풀려 어두운 그림자를 깔고, 그 위에 흰 획을 얹는다

3번이 이 파일의 핵심이다. 2번까지만 하면 **사진에 원래 있던 밝고 가는 것**이 전부
손글씨로 딸려 온다 — 2026-09-12 실측에서 나뭇잎 사이로 뚫린 하늘이 흰 얼룩으로,
흰 운동화와 흰 털이 정체불명의 흰 덩어리로 얹혔다. 손글씨는 **원본에 없다가 새로
생긴 것**이므로, 원본에서 같은 성질을 보이는 자리를 미리 지도로 만들어 빼야 한다.

빼는 기준을 "밝기" 가 아니라 "밝고 **가늘게 튀는 것**" 으로 잡은 이유가 있다.
밝기만으로 빼면 매끈한 하늘 위에 쓴 흰 글씨까지 같이 사라진다. 하늘은 밝지만
**튀지 않는다** — 그래서 하늘 위 글씨는 살고, 나뭇잎 틈은 죽는다.

4번의 그림자는 밝은 배경 위의 흰 글씨가 묻히는 것을 막는다.

## 한계

**피사체 외곽선은 살릴 수 없다.** 생성물 속 피사체 위치가 원본과 미세하게 달라서,
외곽선을 그대로 얹으면 몸에서 벗어나 유령처럼 뜬다. 그래서 프롬프트에서 외곽선을
그리지 말라고 막았다. 글씨·화살표·장식은 여백에 있어 정렬이 필요 없다.
"""

import io

from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat

from .types import ImageInput

#: 최종 카드의 긴 변. 생성 캔버스와 같은 눈금이라 글씨 크기가 의도대로 보인다.
#: 원본 해상도 그대로 두면 한 장에 20MB 가 넘어 S3 와 앱 양쪽에 부담이다.
LONG_EDGE = 1536

#: 국소 대비를 볼 반경. 크면 굵은 획까지 잡고, 작으면 얇은 획만 남는다.
_BLUR_RADIUS = 14

#: 획으로 인정할 문턱. 낮추면 배경 잡티가 섞이고, 높이면 옅은 획이 사라진다.
_POP_MIN, _POP_SPAN = 12, 28
_WHITE_MIN, _WHITE_SPAN = 150, 70

#: 원본 쪽 "밝고 가는 것" 지도를 얼마나 부풀릴지. 생성물 속 피사체 위치가 원본과
#: 미세하게 어긋나므로, 딱 맞게 빼면 경계가 한두 픽셀씩 새어 나온다.
_DECOY_GROW, _DECOY_BLUR = 5, 2

#: 손글씨 레이어(검은 바탕 + 흰 획)를 받았을 때 쓰는 눈금. 추측할 것이 없어서
#: 밝기 하나로 끝난다 — 이 모드의 존재 이유가 그것이다.
_PLATE_MIN, _PLATE_SPAN = 45, 90

#: 레이어가 제대로 왔는지 보는 눈금. 손글씨는 화면의 몇 %도 안 차지하므로 평균이
#: 아주 어둡다. 모델이 지시를 무시하고 사진을 그려 보내면 여기서 걸린다.
_PLATE_MAX_MEAN = 60

#: 획을 아주 살짝 부풀린다. 검은 판에 그은 획은 사진 위에 얹으면 가늘어 보인다.
#:
#: `MaxFilter` 는 홀수 크기만 받아서 제일 약한 값이 한 쪽당 1픽셀이고, 그것도 두껍다 —
#: 글자 크기를 참고 카드에 맞춰 줄이고 나니 더 그렇다. 그래서 흐리게 만든 뒤 문턱을
#: 낮춰 되살리는 방법을 쓴다. 흐림 반경과 문턱으로 **1픽셀보다 작게** 조절할 수 있다.
#: 이 값으로 획 두께가 약 25% 늘어난다(합성 전 획 4px 기준 실측).
_INK_BLUR, _INK_FLOOR, _INK_SPAN = 1.2, 40, 100

#: 그림자. 밝은 하늘 위에서도 흰 글씨가 읽히게 한다. 진하면 글씨 둘레가 지저분해지고
#: 획이 더 가늘어 보여서, 넓게 퍼뜨리되 옅게 깐다.
_SHADOW_GROW, _SHADOW_BLUR, _SHADOW_STRENGTH = 5, 6, 0.38
_SHADOW_COLOR = (30, 30, 35)


class RenderError(Exception):
    """합성에 실패했다."""


def _ramp(image: Image.Image, floor: int, span: int) -> Image.Image:
    """floor 아래는 0, floor+span 위는 255 로 펴는 변환.

    `point` 는 값 하나당 한 번만 부르고 나머지는 룩업 테이블이라 픽셀 수와 무관하게 빠르다.
    파이썬 루프로 돌면 1536px 한 장에 몇 초가 걸린다.
    """
    return image.point([max(0, min(255, (v - floor) * 255 // span)) for v in range(256)])


def _bright_and_thin(image: Image.Image) -> Image.Image:
    """"주변보다 밝고, 흰색에 가까운" 정도. 손글씨가 가진 성질이다."""
    gray = image.convert("L")
    local = gray.filter(ImageFilter.GaussianBlur(_BLUR_RADIUS))

    # ① 주변보다 얼마나 튀는가. 배경이 밝든 어둡든 획은 주변보다 밝다.
    #    매끈한 하늘은 밝아도 튀지 않으므로 여기서 0 이 된다 — 그래서 하늘 위 글씨가 산다.
    pop = _ramp(ImageChops.subtract(gray, local), _POP_MIN, _POP_SPAN)

    # ② 흰색에 가까운가. 세 채널 중 가장 어두운 값으로 본다 — 색이 섞이면 떨어진다.
    red, green, blue = image.split()
    white = _ramp(ImageChops.darker(ImageChops.darker(red, green), blue), _WHITE_MIN, _WHITE_SPAN)

    return ImageChops.multiply(pop, white)


def _ink_mask(card: Image.Image, base: Image.Image) -> Image.Image:
    """생성 카드에서 **원본에 없던** 손글씨 획만 남긴 알파 마스크."""
    ink = _bright_and_thin(card)

    # 원본에도 같은 성질이 있는 자리 — 나뭇잎 틈 하늘, 흰 운동화, 흰 털.
    # 손글씨가 아니라 사진 자체다. 살짝 부풀려 빼야 경계가 새지 않는다.
    decoy = _bright_and_thin(base)
    decoy = decoy.filter(ImageFilter.MaxFilter(_DECOY_GROW))
    decoy = decoy.filter(ImageFilter.GaussianBlur(_DECOY_BLUR))

    ink = ImageChops.multiply(ink, ImageChops.invert(decoy))

    # 끝으로 점점이 흩어진 잡티를 없앤다.
    return ink.filter(ImageFilter.MedianFilter(3))


def _prepare(original: ImageInput, card_png: bytes) -> tuple[Image.Image, Image.Image]:
    """원본과 생성 카드를 같은 크기로 맞춰 돌려준다."""
    try:
        base = Image.open(io.BytesIO(original.data))
        # 휴대폰 사진은 회전 정보가 EXIF 에만 있다. 여기서 실제로 돌려놓는다.
        base = ImageOps.exif_transpose(base).convert("RGB")
        card = Image.open(io.BytesIO(card_png)).convert("RGB")
    except Exception as error:  # noqa: BLE001
        raise RenderError(f"이미지를 열지 못했습니다: {error}") from error

    # 최종 크기를 먼저 정하고 둘 다 거기에 맞춘다. 원본 해상도로 합성하면 느리고 무겁다.
    ratio = LONG_EDGE / max(base.size)
    target = (max(1, round(base.width * ratio)), max(1, round(base.height * ratio)))
    return base.resize(target, Image.LANCZOS), card.resize(target, Image.LANCZOS)


def _thicken(ink: Image.Image) -> Image.Image:
    """획을 1픽셀보다 작은 폭으로 부풀린다."""
    spread = ink.filter(ImageFilter.GaussianBlur(_INK_BLUR))
    return ImageChops.lighter(ink, _ramp(spread, _INK_FLOOR, _INK_SPAN))


def _paint(base: Image.Image, ink: Image.Image) -> bytes:
    """마스크대로 원본에 그림자를 깔고 흰 획을 얹어 PNG 로 굽는다."""
    target = base.size

    shadow = ink.filter(ImageFilter.MaxFilter(_SHADOW_GROW))
    shadow = shadow.filter(ImageFilter.GaussianBlur(_SHADOW_BLUR))
    shadow = shadow.point([int(v * _SHADOW_STRENGTH) for v in range(256)])

    out = Image.composite(Image.new("RGB", target, _SHADOW_COLOR), base, shadow)
    out = Image.composite(Image.new("RGB", target, (255, 255, 255)), out, ink)

    buffer = io.BytesIO()
    out.save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


def compose(original: ImageInput, card_png: bytes) -> bytes:
    """원본 사진 위에 생성 카드의 손글씨만 얹어 최종 카드를 만든다."""
    base, card = _prepare(original, card_png)
    return _paint(base, _ink_mask(card, base))


def compose_from_plate(original: ImageInput, plate_png: bytes) -> bytes:
    """**검은 바탕 + 흰 손글씨** 레이어를 원본에 얹는다.

    위의 `compose` 는 사진과 손글씨가 섞인 그림에서 손글씨를 **추측해서** 꺼낸다.
    이쪽은 추측이 없다 — 배경이 검으니 밝은 것이 곧 손글씨다. 흰 털도 흰 운동화도
    나뭇잎 틈 하늘도 애초에 레이어에 없다.
    """
    base, plate = _prepare(original, plate_png)
    gray = plate.convert("L")

    mean = ImageStat.Stat(gray).mean[0]
    if mean > _PLATE_MAX_MEAN:
        raise RenderError(
            f"손글씨 레이어가 아니라 사진이 왔습니다 (평균 밝기 {mean:.0f}). "
            "모델이 '배경을 검게' 지시를 따르지 않았습니다."
        )

    ink = _ramp(gray, _PLATE_MIN, _PLATE_SPAN).filter(ImageFilter.MedianFilter(3))
    return _paint(base, _thicken(ink))


def save_mask(original: ImageInput, card_png: bytes, path) -> None:
    """마스크를 흑백 PNG 로 떨어뜨린다 — 확인용이고 파이프라인은 쓰지 않는다.

    결과가 이상할 때 "무엇을 손글씨로 쳤는가" 를 눈으로 보는 것이 제일 빠르다.
    글자 모양만 하얗게 보이면 정상이고, 하늘·털·신발이 하얗게 보이면 눈금이 무딘 것이다.
    """
    base, card = _prepare(original, card_png)
    _ink_mask(card, base).save(path, "PNG", optimize=True)
