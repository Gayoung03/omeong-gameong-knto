"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Omeong Gameong API"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://omeong:omeong@localhost:5432/omeong"
    cors_origins: list[str] = ["http://localhost:8081", "http://localhost:19006"]
    aws_region: str = "ap-northeast-2"
    s3_bucket_name: str = ""
    s3_public_base_url: str = ""
    tmap_api: str = ""
    kakao_rest_api_key: str = ""
    weather_api_key: str = ""
    tour_api_key: str = ""

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
    return Settings()


settings = get_settings()
