"""Shared FastAPI dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db

# 개발용 고정 사용자. scripts/seed_dev.py 가 이 id 로 계정을 심는다.
# 팀원 A 와 공유한 값이라 바꾸지 않는다.
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_current_user(db: Annotated[Session, Depends(get_db)]) -> User:
    """현재 로그인한 사용자.

    지금은 개발용 고정 사용자를 돌려주는 임시 구현이다.
    인증 담당이 Authorization 헤더의 JWT 를 검증하는 방식으로
    **이 함수 안쪽만** 바꾸면 된다 — 시그니처(User 반환)가 그대로면
    엔드포인트는 한 줄도 고칠 필요가 없다.

    테스트에서는 app.dependency_overrides[get_current_user] 로 갈아끼운다.
    """
    user = db.get(User, DEV_USER_ID)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
        )
    return user


# 엔드포인트에서 `current_user: CurrentUser` 한 줄로 쓴다.
CurrentUser = Annotated[User, Depends(get_current_user)]
