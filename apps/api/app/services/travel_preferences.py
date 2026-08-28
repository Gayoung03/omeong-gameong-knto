"""여행 취향(user_travel_preferences) upsert 도메인 로직.

## 왜 upsert 하나

`user_travel_preferences` 는 사용자당 한 행이다(PK = `user_id`). 가입
(`POST /auth/signup`)은 이 행을 **처음 만들고**, 이후 `PUT /users/me/travel-preference`
는 **같은 행을 갱신**한다(docs/api/auth.md·users.md). 두 경로가 "없으면 만들고
있으면 고친다"를 각자 구현하면 규칙이 갈린다. 그래서 upsert 를 여기 한 곳에 둔다.

## 트랜잭션 경계·부분 갱신

`add`/`setattr` 후 **`flush` 까지만** 한다 — commit 은 호출자 몫(가입은 계정·펫·
취향을 한 트랜잭션에 함께 커밋한다). 갱신은 **넘어온 필드만** 바꾼다(부분 갱신):
호출자가 `model_dump(exclude_unset=True)` 로 실제로 보낸 필드만 넘기면, 보내지 않은
필드는 그대로 유지된다. 값 검증(예: `companion_count >= 1`)은 요청 스키마와 DB
CheckConstraint 가 맡고, 이 서비스는 upsert 기계 부분만 책임진다.
"""

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import UserTravelPreference


def upsert_travel_preference(
    db: Session, user_id: uuid.UUID, values: Mapping[str, Any]
) -> UserTravelPreference:
    """`user_id` 의 취향 행을 없으면 만들고 있으면 갱신한다.

    `values` 는 설정할 필드만 담는다(부분 갱신). 생성 시 `companion_count` 를
    넘기지 않으면 DB server_default(1)가 적용된다. `add`/`setattr` 후 `flush` 까지만
    하고 commit 하지 않는다.
    """
    preference = db.get(UserTravelPreference, user_id)
    if preference is None:
        preference = UserTravelPreference(user_id=user_id, **values)
        db.add(preference)
    else:
        for field, value in values.items():
            setattr(preference, field, value)
    db.flush()
    return preference
