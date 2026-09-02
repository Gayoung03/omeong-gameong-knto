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

    # --- 메일 발송 (SMTP) --------------------------------------------------
    #: host·username·password 가 모두 채워져야 실제로 보낸다. 하나라도 비면
    #: `services/email.py` 가 로그 스텁으로 떨어진다 — 팀원 로컬과 CI 에 메일
    #: 계정을 나눠 주지 않으므로, 설정이 없다고 기동을 막으면 메일과 무관한
    #: 작업을 하는 사람의 서버가 안 뜬다.
    smtp_host: str = ""
    #: 465 = 접속부터 SSL, 587 = 접속 후 STARTTLS. 네이버는 465 다.
    smtp_port: int = 465
    smtp_use_ssl: bool = True
    #: 네이버·Gmail 은 로그인 비밀번호가 아니라 **애플리케이션 비밀번호**를 받는다.
    smtp_username: str = ""
    smtp_password: str = ""
    #: 실제 From 주소. 로그인 계정과 다른 주소로 보내면 대부분의 메일 서버가
    #: 거절하므로, 비워두면 smtp_username 을 그대로 쓴다.
    smtp_from_email: str = ""
    #: 받는 사람 메일함에 보이는 발신자 이름.
    smtp_from_name: str = "오멍가멍"
    #: 메일 서버가 응답하지 않을 때 포기하는 시간. **무제한으로 두면 안 된다** —
    #: 발송은 백그라운드 스레드에서 도는데 거기서 영영 멈추면 스레드풀이 차서
    #: 메일과 무관한 요청까지 밀린다.
    smtp_timeout_seconds: float = 10.0

    # --- 비밀번호 재설정 ---------------------------------------------------
    #: 인증 코드 유효 시간(분). 짧을수록 메일함이 나중에 털렸을 때 안전하고,
    #: 길수록 메일이 늦게 도착해도 쓸 수 있다. 10분은 그 절충이다.
    password_reset_code_ttl_minutes: int = 10
    #: 코드 하나에 허용하는 입력 시도 횟수. 넘으면 그 코드를 폐기한다 —
    #: 6자리(100만 조합)를 자동으로 찔러 맞추지 못하게 막는 유일한 방어다.
    password_reset_max_attempts: int = 5
    #: 한 계정에 1시간 동안 보낼 수 있는 코드 메일 수(메일함 폭탄 방지).
    password_reset_hourly_limit: int = 5

    # --- 루트 요청 자유문 추출 --------------------------------------------
    # requestText → 표준 태그. 백그라운드 생성 단계라 짧게 자르고 실패는 무시한다.
    request_intent_model: str = "gpt-4o-mini"
    request_intent_timeout_seconds: float = 10.0

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
