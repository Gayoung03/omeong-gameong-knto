"""여행기록 이미지 생성 — 카드 파이프라인과 저장소를 잇는 자리.

## 하는 일은 배관뿐이다

카드를 어떻게 만드는지는 `travel_card/` 가 전부 알고 있고(다섯 단계·손글씨 합성·
안전 판정), 이 파일은 **그 앞뒤만** 잇는다.

    원본 키 읽기 --> build_card() --> 결과 PNG 올리기 --> 공개 주소 반환

그래서 카드 품질에 관한 판단은 여기에 두지 않는다. `ink_plate` 와 `loose` 두 개만
여기서 정하는데, 둘 다 **이미 결론이 난 값**이라 인자로 받지 않는다
(백엔드 작업노트 12번 — 레이어 방식 채택, 배치는 loose 가 사장님 선택).

## 실패를 예외로 바꿔 던진다

`build_card()` 는 실패도 값으로 돌려준다(`CardResult.outcome`). 그런데 부르는 쪽인
`endpoints/travel_logs.py` 의 뒷작업은 **성공이면 주소를 쓰고 실패면 상태를 바꾼다**는
두 갈래뿐이라, 값으로 받으면 `if not result.ok` 를 거기서 또 쓰게 된다. 파이프라인
안쪽에서 네 결말을 구분하는 것과 여기서 두 갈래로 좁히는 것은 층이 다른 일이다.

`ImageGenerationError.user_message` 가 **화면에 그대로 띄울 한국어**다.
`CardResult.message` 를 그대로 쓰지 않는 이유는 그 값에 기술적 사유가 괄호로 붙어
있어서다 — 타임아웃 메시지나 HTTP 코드가 사용자 화면에 보인다. 화면에는
`agent.MESSAGES` 를, 서버 로그에는 `CardResult.message` 를 쓴다.

## 아직 안 쓰는 것 — mood

앱은 기분(`행복했수다`·`신났댕` 등)을 받아 저장하는데 **카드 문구에는 반영되지
않는다.** `caption.generate()` 가 기분을 인자로 받지 않기 때문이다. 인자를 지우지
않고 남겨 둔 것은, 넘길 자리가 생겼을 때 부르는 쪽을 고치지 않게 하려는 것이다.
"""

import logging

from app.db.models.enums import MomentMood, WritingStyle
from app.integrations import storage

from .travel_card import config as card_config
from .travel_card.agent import MESSAGES as CARD_MESSAGES
from .travel_card.agent import build_card
from .travel_card.types import CardOutcome
from .travel_card.types import WritingStyle as CardWritingStyle

logger = logging.getLogger(__name__)

#: 원인을 모를 때 보여줄 말. `CardOutcome.FAILED` 와 같은 문구를 쓴다 —
#: 사용자가 할 수 있는 일이 "다시 시도" 하나라는 점에서 같은 상황이다.
DEFAULT_FAILURE_MESSAGE = CARD_MESSAGES[CardOutcome.FAILED]

#: 완성 카드가 올라갈 접두사. `uploads.py` 의 `travel-log/`(원본)와 **구분한다** —
#: 원본과 결과물은 보관 기간·정리 기준이 달라질 수 있다(팀 안건: uploads.md 갱신).
CARD_PREFIX = "travel-log-card"


class ImageGenerationError(RuntimeError):
    """이미지를 만들지 못했다. 부르는 쪽이 generation_status 를 failed 로 바꾼다.

    `user_message` 는 화면에 그대로 띄울 한국어다. 기본값을 둔 이유는 이 예외를
    던지는 자리마다 문구를 고르게 하면 언젠가 빈 문자열이 화면에 나가기 때문이다.
    """

    def __init__(self, reason: str, *, user_message: str = DEFAULT_FAILURE_MESSAGE) -> None:
        super().__init__(reason)
        self.user_message = user_message


def generate_log_image(
    original_image_url: str,
    writing_style: WritingStyle,
    mood: MomentMood | None,
    place_name: str,
    *,
    pet_name: str | None = None,
    date_text: str | None = None,
) -> str:
    """완성 카드의 공개 주소를 돌려준다. 실패하면 `ImageGenerationError`.

    `mood` 는 아직 파이프라인에 넘길 자리가 없다(모듈 설명 참고).
    """
    del mood

    if not card_config.api_key():
        # 키가 없으면 첫 LLM 호출에서 실패한다. 돈이 드는 단계 전에 끊는다.
        raise ImageGenerationError("OPENAI_API_KEY 가 없습니다")

    if not storage.is_configured():
        raise ImageGenerationError("S3 설정이 없습니다(S3_BUCKET_NAME·S3_PUBLIC_BASE_URL)")

    object_key = storage.object_key_from_public_url(original_image_url)
    if object_key is None:
        # 우리 버킷 주소가 아니다. 스키마 검증(schemas/validators.py)을 통과했더라도
        # 키를 못 떼면 읽을 방법이 없다 — 주소는 남기지 않고 사실만 남긴다.
        raise ImageGenerationError("원본 주소가 우리 저장소 것이 아닙니다")

    try:
        original = storage.download(object_key, max_bytes=card_config.MAX_IMAGE_BYTES)
    except storage.StorageError as error:
        raise ImageGenerationError(str(error)) from error

    result = build_card(
        original,
        CardWritingStyle(writing_style.value),
        pet_name=pet_name,
        place_name=place_name,
        date_text=date_text,
        # 둘 다 작업노트 12번에서 결론이 난 값이다. 바꾸려면 카드를 눈으로 다시 봐야 한다.
        ink_plate=True,
        loose=True,
    )

    if not result.ok or result.png is None:
        # 사유(`result.message`)는 로그에만. 괄호 안 기술적 설명이 화면에 나가면 안 된다.
        logger.warning(
            "카드 생성 실패: outcome=%s reason=%s timings=%s",
            result.outcome,
            result.message,
            result.timings,
        )
        raise ImageGenerationError(
            f"카드 생성 실패({result.outcome})",
            user_message=CARD_MESSAGES.get(result.outcome, DEFAULT_FAILURE_MESSAGE),
        )

    logger.info(
        "카드 생성 완료: %s -> %s (%s초)",
        result.source_size,
        result.result_size,
        sum(result.timings.values()),
    )

    try:
        return storage.upload(
            result.png,
            object_key=storage.build_object_key(CARD_PREFIX, "png"),
            content_type="image/png",
        )
    except storage.StorageError as error:
        # 카드는 만들어졌는데 올리지 못한 경우다. 돈은 이미 나갔으므로 로그에 남긴다.
        logger.error("카드를 만들었지만 올리지 못했습니다: %s", error)
        raise ImageGenerationError(str(error)) from error
