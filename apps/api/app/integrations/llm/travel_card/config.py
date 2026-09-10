"""카드 파이프라인 설정.

모델명은 코드에 두지 않고 환경변수로 받는다 — 저장소의 다른 LLM 기능과 같은 규칙이다
(`app/core/config.py` 의 openai_model·route_edit_model 주석 참고).

## 왜 core/config.py 의 Settings 에 넣지 않았나

아직 API 라우트가 없어 서버 기동과 무관하다. 공용 설정 파일을 먼저 늘리면 이 기능과
상관없는 팀원의 로컬 기동에 영향이 간다. 라우트를 붙일 때 Settings 로 옮긴다.

## 그런데 os.getenv 만 쓰면 안 된다

키와 모델명은 `.env` 파일에 있고 셸에 export 돼 있지 않다. `os.getenv` 만 쓰면
로컬에서 항상 "키가 없습니다" 가 된다. 그래서 여기서도 **같은 `.env` 파일을 읽는**
BaseSettings 를 쓴다 — 클래스만 분리했을 뿐 읽는 곳은 저장소 전체와 같다.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class TravelCardSettings(BaseSettings):
    #: 챗봇과 같은 키를 쓴다. 없으면 빈 문자열 — 부르는 쪽이 판단한다.
    openai_api_key: str = ""

    #: 사진 분석. 이미지를 읽어야 하므로 멀티모달 모델이어야 한다.
    travel_card_vision_model: str = "gpt-4o-mini"
    #: 메모 생성. 이미지를 안 보고 분석 결과만 읽으므로 텍스트 모델로 충분하다.
    travel_card_caption_model: str = "gpt-4o-mini"
    #: 이미지 편집. 후보: gpt-image-1-mini(저렴) · gpt-image-2(품질).
    #: gpt-image-1 은 2026-10-23 폐기 예정이라 신규로 쓰지 않는다.
    travel_card_image_model: str = "gpt-image-1-mini"
    #: low / medium / high. 비용이 여기서 몇 배로 갈린다.
    travel_card_image_quality: str = "medium"

    #: 타임아웃(초). 이미지 편집은 느리다 — 30초로 잡으면 정상 요청이 잘린다.
    travel_card_vision_timeout: float = 30.0
    travel_card_caption_timeout: float = 30.0
    travel_card_image_timeout: float = 180.0

    #: 메모 개수. 많을수록 사진이 가려지고 한글이 깨질 확률이 올라간다.
    #: 6개가 적정이라고 눈으로 확인했다(2026-09-09 실측) — 8개는 하늘이 글자로 찼다.
    #: 하한을 4로 둔 것은 "재료가 모자라면 적게 쓰라"는 지시와 짝을 맞추기 위해서다.
    travel_card_min_memos: int = 4
    travel_card_max_memos: int = 6

    # `core/config.py` 와 같은 파일을 같은 순서로 읽는다.
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> TravelCardSettings:
    return TravelCardSettings()


_settings = get_settings()

VISION_MODEL = _settings.travel_card_vision_model
CAPTION_MODEL = _settings.travel_card_caption_model
IMAGE_MODEL = _settings.travel_card_image_model
IMAGE_QUALITY = _settings.travel_card_image_quality

VISION_TIMEOUT = _settings.travel_card_vision_timeout
CAPTION_TIMEOUT = _settings.travel_card_caption_timeout
IMAGE_TIMEOUT = _settings.travel_card_image_timeout

MIN_MEMOS = _settings.travel_card_min_memos
MAX_MEMOS = _settings.travel_card_max_memos

# 둘 중 하나만 환경변수로 덮으면 "메모 8~6개" 같은 앞뒤 안 맞는 범위가 모델에 나간다.
# 실제로 겪었다(2026-09-09) — 모델은 8개를 만들고 코드가 뒤 2개를 잘라냈다.
if MIN_MEMOS > MAX_MEMOS:
    MIN_MEMOS = MAX_MEMOS

#: 원본 사진 상한. `endpoints/uploads.py` 의 MAX_FILE_SIZE 와 같은 값으로 맞춘다.
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def api_key() -> str:
    """없으면 빈 문자열. 부르는 쪽이 판단한다 — 여기서 예외를 던지지 않는다."""
    return _settings.openai_api_key
