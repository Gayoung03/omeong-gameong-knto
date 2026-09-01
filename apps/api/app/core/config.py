"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

#: SECRET_KEY 가 없을 때 기동 로그에 남길 안내. Pydantic 기본 메시지("Field
#: required")는 무엇을 어디에 넣어야 하는지 알려주지 않아 사람이 읽을 수 있게 바꾼다.
#: HS256 서명 키의 최소 길이. RFC 7518 §3.2 는 HMAC-SHA256 키를 최소 32바이트로
#: 권장한다 — 짧은 키는 무차별 대입에 약하다.
_SECRET_KEY_MIN_LENGTH = 32
_MISSING_SECRET_KEY_MESSAGE = (
    f"SECRET_KEY가 없거나 너무 짧습니다({_SECRET_KEY_MIN_LENGTH}자 이상 필요) — .env.example 참고"
)


class Settings(BaseSettings):
    app_name: str = "Omeong Gameong API"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    #: JWT 서명 키. 기본값을 두지 않고 32자 미만도 막는다 — 짧거나 뻔한 키는 서명을
    #: 위조당할 여지가 있다. `.env.example` 의 빈 `SECRET_KEY=` 를 그대로 복사하거나
    #: 짧은 값을 넣으면 기동에서 즉시 실패한다(아래 get_settings 의 안내 메시지 참고).
    secret_key: str = Field(min_length=_SECRET_KEY_MIN_LENGTH)
    database_url: str = "postgresql+psycopg://omeong:omeong@localhost:5432/omeong"
    cors_origins: list[str] = ["http://localhost:8081", "http://localhost:19006"]
    aws_region: str = "ap-northeast-2"
    s3_bucket_name: str = ""
    s3_public_base_url: str = ""
    tmap_api: str = ""
    kakao_rest_api_key: str = ""
    weather_api_key: str = ""
    tour_api_key: str = ""
    web_push_vapid_public_key: str = ""
    web_push_vapid_private_key: str = ""
    web_push_vapid_subject: str = ""

    # --- 소셜 로그인 (카카오) -------------------------------------------
    #: 카카오 로그인 REST 앱 키(client_id). 인가·토큰 교환에 쓴다.
    #: kakao_rest_api_key 를 그대로 사용한다(위).
    #: 보안 강화가 켜져 있으면 필요한 client_secret. 없으면 교환에서 생략한다.
    kakao_client_secret: str = ""
    #: access_token_info 로 받은 app_id 가 우리 앱인지 대조할 값. 설정 시에만 검증.
    kakao_app_id: str = ""
    #: 카카오 콘솔에 등록한 Redirect URI. 인가·토큰 교환에서 같은 값을 써야 한다.
    kakao_redirect_uri: str = ""
    #: returnUrl 허용 프리픽스(콤마 구분). 비어 있으면 local 은 exp://·http://localhost
    #: 를 기본 허용하고, 그 외 환경은 아무것도 허용하지 않는다(전부 422 — 설정 필수).
    oauth_return_url_prefixes: str = ""

    # --- 챗봇 -------------------------------------------------------------
    openai_api_key: str = ""
    #: 모델은 설정값이라 코드를 고치지 않고 바꾼다. 저렴한 소형부터 시작하고
    #: 품질이 모자라면 올린다(설계 결정 C1).
    openai_model: str = "gpt-4o-mini"
    #: 첫 응답까지 20초, 전체 60초(설계 결정 E2).
    chat_connect_timeout_seconds: float = 20.0
    chat_timeout_seconds: float = 60.0
    #: 사용자 한 명이 하루에 보낼 수 있는 질문 수(설계 결정 E3).
    #: `environment` 가 local 이면 제한하지 않는다 — 개발·시연 중에 막히면 곤란하다.
    chat_daily_limit: int = 15

    # --- 루트 부분 수정 ---------------------------------------------------
    # 일반 챗봇과 프롬프트·호출 경로·모델 설정을 공유하지 않는다.
    route_edit_model: str = "gpt-4o-mini"
    route_edit_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        # 누락(missing)이든 빈 문자열(too_short)이든 SECRET_KEY 문제면 같은 안내로.
        secret_key_problem = any(
            entry["loc"] == ("secret_key",) for entry in error.errors()
        )
        if secret_key_problem:
            raise RuntimeError(_MISSING_SECRET_KEY_MESSAGE) from error
        raise


settings = get_settings()
