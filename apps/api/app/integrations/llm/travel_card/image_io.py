"""원본 사진을 읽고 크기를 알아낸다.

스펙의 모듈 목록에는 없지만 따로 뺐다. 파일을 못 읽는 것은 **LLM 과 무관한 실패**이고
(`CardOutcome.UNREADABLE_IMAGE`), vision·image_edit 두 곳이 같은 정보를 필요로 한다.

**Pillow 를 쓰지 않는다.** 필요한 것이 폭·높이뿐이라 헤더만 읽으면 된다.
의존성 하나를 아끼려는 것이 아니라, 이 단계에서 새 라이브러리를 넣으면 팀원이
`uv sync` 를 돌려야 하기 때문이다(머지 노트 1번 표 대상이 된다).
"""

import struct

from .config import MAX_IMAGE_BYTES
from .types import ImageInput


class UnreadableImage(Exception):
    """포맷 불일치·손상·용량 초과. 부르는 쪽이 UNREADABLE_IMAGE 로 바꾼다."""


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
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime, size = "image/png", _png_size(data)
    elif len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        mime, size = "image/webp", _webp_size(data)
    else:
        raise UnreadableImage("JPEG, PNG, WebP 만 쓸 수 있습니다")

    if size is None or size[0] <= 0 or size[1] <= 0:
        raise UnreadableImage("이미지 크기를 읽지 못했습니다")

    return ImageInput(data=data, mime_type=mime, width=size[0], height=size[1])
