"""요청 스키마가 공유하는 검증자.

## 이미지 URL 출처 검증 — 왜 필요한가

프로필·반려동물·리뷰·여행기록·여행 커버 이미지는 모두 앱이 `POST /uploads` 로
먼저 올리고 받은 주소를 그대로 요청에 넣는다(docs/api/uploads.md). 그런데 이
값을 그대로 믿으면 우리 저장소가 아닌 **아무 외부 주소**를 이미지로 박아 넣을 수
있다 — 다른 사용자에게 그 주소가 그대로 렌더링되면 추적 픽셀·피싱 이미지·SSRF
프리뷰의 통로가 된다.

그래서 허용 호스트(`settings.s3_public_base_url` 의 호스트) 하나와 **정확히**
일치하는 절대 URL 만 통과시킨다.

- **`startswith` 를 쓰지 않는다.** `https://<허용호스트>@evil.com/x` 은
  `startswith("https://<허용호스트>")` 를 통과하지만 실제 접속 대상은 `evil.com`
  이다. `urlsplit(...).hostname` 으로 파싱한 호스트만 비교한다.
- 대소문자는 호스트에서 의미가 없으므로 소문자로 맞춰 비교한다.

허용 호스트가 설정돼 있지 않을 때(로컬 개발·S3 미연동)는 환경에 따라 가른다 —
`local` 은 경고만 남기고 통과시키고(개발이 막히면 곤란하다), 그 외 환경은 출처를
확인할 수 없으므로 절대 URL 을 전부 거부한다.
"""

import logging
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import AfterValidator

from app.core.config import settings

logger = logging.getLogger(__name__)


def _allowed_image_host() -> str | None:
    """허용 이미지 호스트. 설정이 비어 있으면 None."""
    base = settings.s3_public_base_url
    if not base:
        return None
    return (urlsplit(base).hostname or "").lower() or None


def validate_image_url(value: str | None) -> str | None:
    """이미지 URL 이 우리 저장소 출처인지 확인한다.

    None 은 그대로 통과한다(선택 필드). 나머지는 위 모듈 설명의 규칙을 따른다.
    실패는 `ValueError` — Pydantic 이 422 로 바꾼다.
    """
    if value is None:
        return value

    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    is_absolute = bool(parsed.scheme or parsed.netloc)
    allowed_host = _allowed_image_host()

    if allowed_host is None:
        # 허용 호스트를 알 수 없다 — 출처를 검증할 방법이 없다.
        if settings.environment == "local":
            if is_absolute:
                # 좌표·토큰이 아니라 호스트만 남긴다. 그대로도 민감하지 않다.
                logger.warning(
                    "이미지 URL 출처 검증 생략 (S3_PUBLIC_BASE_URL 미설정, local): host=%s",
                    host or "-",
                )
            return value
        raise ValueError("이미지 URL 출처를 확인할 수 없습니다")

    if host != allowed_host:
        raise ValueError("허용되지 않은 이미지 URL 출처입니다")
    return value


#: 선택 이미지 URL 필드(`str | None`)에 붙인다.
OptionalImageUrl = Annotated[str | None, AfterValidator(validate_image_url)]

#: 필수 이미지 URL 필드(`str`)에 붙인다. 리스트 항목에도 이걸 쓴다.
ImageUrl = Annotated[str, AfterValidator(validate_image_url)]
