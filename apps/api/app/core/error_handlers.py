"""전역 예외 핸들러.

## 왜 기본 핸들러를 바꾸나

- **422 입력값 에코 제거** — FastAPI 기본 검증 오류는 항목마다 `input`(사용자가
  보낸 원래 값)과 `ctx`(검증 컨텍스트)를 그대로 돌려준다. 비밀번호·토큰처럼
  민감한 값을 보냈다가 검증에 걸리면 그 값이 응답 본문에 그대로 되돌아오고,
  로깅 미들웨어가 응답을 남기면 로그에도 박힌다. `type`·`loc`·`msg` 만 남긴다.
- **무결성 오류 처리** — 동시 요청 경합으로 unique 제약을 어기면 잡지 않은 채
  500 이 나가고, SQLAlchemy 예외 문자열에 제약명·테이블명이 섞여 나간다. unique
  위반은 409 로, 그 외는 안전한 500 으로 바꾸고 **제약명·SQL·파라미터를 응답에도
  로그에도 남기지 않는다.**

두 핸들러 모두 응답 형식은 FastAPI 기본 `{"detail": ...}` 를 유지한다(공통 규약 —
래핑 금지, docs/api/README.md).
"""

import logging

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

#: PostgreSQL unique_violation SQLSTATE.
_UNIQUE_VIOLATION = "23505"

#: 검증 오류 항목에서 지우는 키. `input` 은 사용자가 보낸 원래 값, `ctx` 는
#: 그 값을 포함할 수 있는 검증 컨텍스트다.
_STRIPPED_ERROR_KEYS = ("input", "ctx")


def _sanitize_validation_errors(errors: list[dict]) -> list[dict]:
    return [
        {key: value for key, value in error.items() if key not in _STRIPPED_ERROR_KEYS}
        for error in errors
    ]


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422 응답에서 입력값 에코(`input`·`ctx`)를 제거한다.

    형식은 기본과 같은 `{"detail": [ {type, loc, msg}, ... ]}` 다. `loc` 이 튜플이라
    `jsonable_encoder` 로 직렬화 가능한 형태로 바꿔 내려준다.
    """
    # 코드베이스 관례대로 422 는 리터럴로 쓴다(starlette 의
    # HTTP_422_UNPROCESSABLE_ENTITY 상수는 접근 시 deprecation 경고를 낸다).
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": _sanitize_validation_errors(exc.errors())}),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """잡히지 않은 `IntegrityError` 를 안전한 응답으로 바꾼다.

    unique 위반(동시 요청 경합 등)은 409, 나머지는 500. 어느 쪽도 제약명·테이블명·
    SQL·파라미터를 노출하지 않는다. 진단용으로 남기는 것은 요청 메서드·경로(**쿼리
    스트링 제외** — GPS 좌표 등이 붙을 수 있다)와 SQLSTATE 뿐이다.
    """
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)

    if sqlstate == _UNIQUE_VIOLATION:
        logger.warning(
            "unique 위반: %s %s (sqlstate=%s)", request.method, request.url.path, sqlstate
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "이미 존재하는 리소스입니다"},
        )

    logger.error(
        "예기치 못한 무결성 오류: %s %s (sqlstate=%s, orig=%s)",
        request.method,
        request.url.path,
        sqlstate,
        type(orig).__name__ if orig is not None else None,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "요청을 처리하지 못했습니다"},
    )


def register_error_handlers(app) -> None:
    """앱에 전역 예외 핸들러를 등록한다."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
