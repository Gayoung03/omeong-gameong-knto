"""단계 4 — 이미지 편집 호출. 전체 지연의 대부분이 여기다.

## 비율은 프롬프트로 지키지 못한다

"원본 비율을 유지해줘" 를 프롬프트에 넣어도 소용없다. 이미지 API 는 **정해진 크기
중에서만** 출력한다(1024x1024 · 1536x1024 · 1024x1536). 그래서 원본 비율에 가장 가까운
크기를 **코드에서 골라** `size` 로 넘긴다. 프롬프트의 문장은 모델이 사진을 잘라내지
않게 하는 보조 장치일 뿐이다.

## 거부와 실패를 구분한다

생성 쪽이 안전상 결과물을 거부한 것(`BLOCKED_OUTPUT`)과 네트워크·타임아웃 실패는
사용자에게 다른 안내를 줘야 한다. 벤더 에러 메시지에서 그 둘을 갈라낸다.
"""

import base64
import io

from openai import OpenAI

from .config import IMAGE_MODEL, IMAGE_QUALITY, IMAGE_TIMEOUT, api_key
from .types import ImageInput

#: 이미지 API 가 받아주는 크기. (가로, 세로)
_SIZES = ((1024, 1024), (1536, 1024), (1024, 1536))

#: 벤더가 "안전상 거부" 를 알릴 때 메시지에 섞이는 말들.
_REFUSAL_HINTS = (
    "safety",
    "content_policy",
    "content policy",
    "moderation",
    "rejected",
    "not allowed",
)


class ImageEditError(Exception):
    """이미지를 만들지 못했다."""


class ImageRefused(ImageEditError):
    """생성 쪽이 안전상 거부했다. 사용자에게 다른 안내를 준다."""


def pick_size(image: ImageInput) -> str:
    """원본 비율에 가장 가까운 출력 크기.

    비율 차이를 로그로 비교한다 — 1.5배와 0.667배가 1.0 에서 같은 거리로 취급되게
    하려는 것이다. 산술 차이로 비교하면 세로 사진이 늘 정사각형으로 몰린다.
    """
    import math

    target = math.log(image.aspect) if image.aspect > 0 else 0.0
    best = min(_SIZES, key=lambda wh: abs(math.log(wh[0] / wh[1]) - target))
    return f"{best[0]}x{best[1]}"


def _client() -> OpenAI:
    key = api_key()
    if not key:
        raise ImageEditError("OPENAI_API_KEY 가 설정되지 않았습니다")
    return OpenAI(api_key=key, timeout=IMAGE_TIMEOUT, max_retries=0)


def _extension(mime_type: str) -> str:
    return {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(mime_type, "png")


def edit(image: ImageInput, prompt: str) -> bytes:
    """원본 사진과 프롬프트로 카드 PNG 바이트를 만든다."""
    buffer = io.BytesIO(image.data)
    # SDK 가 파일 이름에서 형식을 읽는다. 이름이 없으면 업로드가 거절된다.
    buffer.name = f"original.{_extension(image.mime_type)}"

    try:
        response = _client().images.edit(
            model=IMAGE_MODEL,
            image=buffer,
            prompt=prompt,
            size=pick_size(image),
            quality=IMAGE_QUALITY,
        )
    except Exception as error:  # noqa: BLE001
        text = str(error).lower()
        if any(hint in text for hint in _REFUSAL_HINTS):
            raise ImageRefused(str(error)) from error
        raise ImageEditError(str(error)) from error

    if not response.data:
        raise ImageEditError("이미지가 비어 있습니다")

    encoded = response.data[0].b64_json
    if not encoded:
        raise ImageEditError("이미지 데이터가 없습니다")
    return base64.b64decode(encoded)
