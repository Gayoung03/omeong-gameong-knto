"""장소 가시성 확인 — 장소를 참조하는 엔드포인트가 공유한다.

## 왜 한 곳에 모으나

사용자가 등록한 "나만의 장소"는 별도 테이블이 아니라 `places` 에 함께 저장되고
`created_by_user_id` 로만 구분된다(endpoints/places.py 모듈 설명 참고). 장소를
`db.get(Place, ...)` 로 그냥 읽으면 **남이 등록한 개인 장소**까지 잡힌다. 리뷰
작성·일정 추가·기록 생성이 각자 `db.get` 을 쓰면, 장소 목록·상세는 남의 개인
장소를 404 로 가리는데 그 쪽 경로들만 조용히 통과하는 구멍이 생긴다.

그래서 "가져오면서 가시성까지" 확인하는 함수를 한 곳에 두고 모두가 쓴다
(services/route_access.py 가 여행 소유권에 대해 하는 것과 같은 패턴).

**남이 등록한 장소는 일괄 404 다.** 403 으로 알려주면 "그 id 의 장소가 존재한다"는
사실이 새어 나간다(장소 상세와 동일 규칙, docs/api/places.md).
"""

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Place, User


def load_visible_place(db: Session, place_id: uuid.UUID, user: User | None) -> Place:
    """볼 수 있는 장소만 돌려준다.

    공식 장소(`created_by_user_id IS NULL`)이거나 내가 등록한 장소여야 한다.
    없거나(비활성 포함) 남의 개인 장소면 404.
    """
    place = db.get(Place, place_id)
    if place is None or not place.is_active:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다")

    is_official = place.created_by_user_id is None
    is_mine = user is not None and place.created_by_user_id == user.id
    if not is_official and not is_mine:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다")

    return place
