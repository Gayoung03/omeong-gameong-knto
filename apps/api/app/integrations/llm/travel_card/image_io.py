"""원본 사진을 읽고 크기를 알아낸다.

스펙의 모듈 목록에는 없지만 따로 뺐다. 파일을 못 읽는 것은 **LLM 과 무관한 실패**이고
(`CardOutcome.UNREADABLE_IMAGE`), vision·image_edit 두 곳이 같은 정보를 필요로 한다.

형식 판정과 크기 읽기는 **헤더만 본다.** 필요한 것이 폭·높이뿐이라 이미지를 통째로
디코딩할 이유가 없다.

`normalize()` 만 Pillow 를 쓴다. 합성 단계 때문에 어차피 들어온 의존성이고,
**업로드 직전에 사진을 한 번 표준화하지 않으면 휴대폰 사진에서 계속 깨진다** —
아래 그 함수의 설명을 볼 것.
"""

import io
import struct

from PIL import Image, ImageOps

from .config import MAX_IMAGE_BYTES
from .types import ImageInput

#: 표준화한 사진의 긴 변. 생성 캔버스가 1536 이라 그보다 여유만 있으면 된다.
#: 4032px 원본을 그대로 올리면 업로드가 길어지고 vision 토큰도 비싸진다.
NORMALIZED_LONG_EDGE = 2048


class UnreadableImage(Exception):
    """포맷 불일치·손상·용량 초과. 부르는 쪽이 UNREADABLE_IMAGE 로 바꾼다."""


def jpeg_orientation(data: bytes) -> int:
    """JPEG 의 EXIF Orientation 값. 없으면 1(회전 없음).

    ## 이걸 안 읽으면 사진이 통째로 재구성된다

    휴대폰은 센서 방향 그대로 저장하고 "돌려서 보라"는 표시만 EXIF 에 남긴다.
    그래서 세로로 찍은 사진이 파일 안에서는 가로 픽셀로 들어 있다.

    이 값을 무시하면 세로 사진을 가로로 착각하고, 이미지 API 에 가로 캔버스를
    요청하게 된다. 모델은 세로 장면을 가로에 담으려고 **장면을 다시 짠다** —
    나무 배치도 사람 위치도 얼굴도 다 바뀐다(2026-09-12 실측).
    """
    if not data.startswith(b"\xff\xd8"):
        return 1
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if i + 4 > len(data):
            return 1
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        segment = data[i + 4 : i + 2 + length]
        if marker == 0xE1 and segment.startswith(b"Exif\x00\x00"):
            return _exif_orientation(segment[6:])
        # SOS 이후는 압축 데이터라 EXIF 가 없다.
        if marker == 0xDA:
            return 1
        i += 2 + length
    return 1


def _exif_orientation(tiff: bytes) -> int:
    """TIFF 헤더에서 Orientation(0x0112) 태그만 꺼낸다."""
    if len(tiff) < 8:
        return 1
    if tiff[:2] == b"II":
        endian = "<"
    elif tiff[:2] == b"MM":
        endian = ">"
    else:
        return 1
    try:
        offset = struct.unpack(endian + "I", tiff[4:8])[0]
        if offset + 2 > len(tiff):
            return 1
        count = struct.unpack(endian + "H", tiff[offset : offset + 2])[0]
        for index in range(count):
            entry = offset + 2 + index * 12
            if entry + 12 > len(tiff):
                return 1
            tag = struct.unpack(endian + "H", tiff[entry : entry + 2])[0]
            if tag == 0x0112:
                value = struct.unpack(endian + "H", tiff[entry + 8 : entry + 10])[0]
                return value if 1 <= value <= 8 else 1
    except struct.error:
        return 1
    return 1


#: 사진을 90도 돌려서 봐야 하는 값들. 폭과 높이를 바꿔야 한다.
_SWAPPED_ORIENTATIONS = (5, 6, 7, 8)


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # SOF0/1/2/3, SOF5~7, SOF9~11, SOF13~15 가 크기를 담는다.
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height, width = struct.unpack(">HH", data[i + 5 : i + 9])
            return width, height
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if i + 4 > len(data):
            return None
        i += 2 + struct.unpack(">H", data[i + 2 : i + 4])[0]
    return None


def _png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24:
        return None
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _webp_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 30:
        return None
    fourcc = data[12:16]
    if fourcc == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    if fourcc == b"VP8 ":
        width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return width, height
    if fourcc == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def load_image(data: bytes) -> ImageInput:
    """바이트에서 형식과 크기를 알아낸다.

    확장자와 클라이언트가 보낸 Content-Type 을 믿지 않고 **내용을 본다** —
    `endpoints/uploads.py` 의 `_detect_image` 와 같은 규칙이다. HEIC 는 여기서 걸린다
    (앱이 JPEG 로 변환해 올리기로 확정: docs/api/uploads.md).
    """
    if not data:
        raise UnreadableImage("빈 파일입니다")
    if len(data) > MAX_IMAGE_BYTES:
        raise UnreadableImage(f"{MAX_IMAGE_BYTES // (1024 * 1024)}MB 이하만 쓸 수 있습니다")

    if data.startswith(b"\xff\xd8\xff"):
        mime, size = "image/jpeg", _jpeg_size(data)
        # 저장된 픽셀이 아니라 **사람이 보는 방향**의 크기를 쓴다.
        if size and jpeg_orientation(data) in _SWAPPED_ORIENTATIONS:
            size = (size[1], size[0])
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime, size = "image/png", _png_size(data)
    elif len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        mime, size = "image/webp", _webp_size(data)
    else:
        raise UnreadableImage("JPEG, PNG, WebP 만 쓸 수 있습니다")

    if size is None or size[0] <= 0 or size[1] <= 0:
        raise UnreadableImage("이미지 크기를 읽지 못했습니다")

    return ImageInput(data=data, mime_type=mime, width=size[0], height=size[1])


def read_png_size(data: bytes) -> str:
    """생성된 PNG 의 크기. 요청한 size 가 지켜졌는지 확인하는 용도다.

    세로 사진을 넣었는데 가로 카드가 나오는 일이 있어(2026-09-10) 눈으로 볼 수 있게 했다.
    """
    size = _png_size(data)
    return f"{size[0]}x{size[1]}" if size else "?"


def normalize(image: ImageInput) -> ImageInput:
    """업로드 직전에 사진을 **평범한 JPEG 한 장**으로 다시 굽는다.

    ## 왜 필요한가

    휴대폰 사진은 겉만 JPEG 인 경우가 많다. 실제로 걸린 것이 **MPO** 였다 —
    듀얼 카메라·심도 정보 때문에 JPEG 두 장이 한 파일에 들어 있는 형식으로,
    앞 4바이트가 JPEG 와 똑같아 형식 판정은 통과하고 OpenAI 가
    `invalid_image_file` 로 거절한다(2026-09-13, 제주_샘플_13).

    한 번 다시 구우면 이 부류가 한꺼번에 정리된다.

        여러 장 묶인 파일(MPO)   -> 첫 장만 남는다
        CMYK·회색조·팔레트       -> RGB 로
        EXIF 회전 표시           -> 픽셀을 실제로 돌려 놓는다
        색 프로파일·메타데이터    -> 떨어져 나간다
        4032px 원본             -> 2048px 로 (업로드·토큰 절약)

    EXIF 회전을 여기서 실제로 적용하는 것이 특히 중요하다. 표시만 남겨두면
    이미지 API 가 그것을 존중하는지 아닌지에 결과가 달려 있게 된다.
    """
    try:
        with Image.open(io.BytesIO(image.data)) as opened:
            # MPO 는 여러 프레임이다. 기본값이 첫 프레임이라 그대로 쓴다.
            picture = ImageOps.exif_transpose(opened).convert("RGB")

            ratio = NORMALIZED_LONG_EDGE / max(picture.size)
            if ratio < 1:
                target = (round(picture.width * ratio), round(picture.height * ratio))
                picture = picture.resize(target, Image.LANCZOS)

            buffer = io.BytesIO()
            picture.save(buffer, "JPEG", quality=92, optimize=True)
            width, height = picture.size
    except Exception as error:  # noqa: BLE001
        raise UnreadableImage(f"사진을 여는 데 실패했습니다: {error}") from error

    return ImageInput(
        data=buffer.getvalue(), mime_type="image/jpeg", width=width, height=height
    )
