"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.error_handlers import register_error_handlers

# 프로덕션에서는 Swagger·ReDoc·OpenAPI 스키마를 모두 닫는다. 전체 API 표면을
# 문서로 노출하면 공격 대상을 그대로 알려주는 셈이다. openapi_url 을 닫으면
# /docs·/redoc 도 스키마를 못 읽어 함께 비활성된다.
_is_production = settings.environment == "production"

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"message": "Omeong Gameong API"}
