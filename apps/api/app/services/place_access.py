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

## 동반 불가인 공식 장소도 404 다

우리는 동반 가능한 장소만 소개한다(2026-08-31 확정). 목록에서만 빼면 예전에
저장해 둔 링크나 id 로 상세·리뷰가 그대로 열려서, 같은 장소가 "없는 곳"이었다가
"동반 불가인데 소개되는 곳"이 된다. 그래서 참조 경로도 함께 막는다.

예외는 **저장 해제 하나뿐이다.** 그것까지 막으면 이미 즐겨찾기해 둔 사용자가
영원히 목록에서 지울 수 없다(`pet_friendly_only=False`).
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Place, PlacePetPolicy, User
from app.db.models.enums import PetPolicyType


def load_visible_place(
    db: Session,
    place_id: uuid.UUID,
    user: User | None,
    *,
    pet_friendly_only: bool = True,
) -> Place:
    """볼 수 있는 장소만 돌려준다.

    공식 장소(`created_by_user_id IS NULL`)이거나 내가 등록한 장소여야 한다.
    없거나(비활성 포함) 남의 개인 장소면 404. 동반 불가인 공식 장소도 404 다.

    `pet_friendly_only=False` 는 **이미 담아 둔 것을 치우는 경로 전용**이다.
    """
    place = db.get(Place, place_id)
    if place is None or not place.is_active:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다")

    is_official = place.created_by_user_id is None
    is_mine = user is not None and place.created_by_user_id == user.id
    if not is_official and not is_mine:
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다")

    # 내가 등록한 장소에는 정책 행이 없다(항상 unknown 으로 나간다). 검사할 것도 없다.
    if pet_friendly_only and is_official and _is_not_allowed(db, place_id):
        raise HTTPException(status_code=404, detail="장소를 찾을 수 없습니다")

    return place


def _is_not_allowed(db: Session, place_id: uuid.UUID) -> bool:
    """동반 불가로 분류된 장소인가.

    정책 행이 없으면 `unknown` 이고, 그건 "동반 여부 모름"이 아니라 "실내·야외
    세부를 모름"이라 통과다(services/place_query.py 의 `pet_friendly_condition`
    과 같은 규칙 — 목록은 SQL 조건으로, 여기는 장소 한 건이라 값을 직접 본다).
    """
    stored = db.scalar(
        select(PlacePetPolicy.policy_type).where(PlacePetPolicy.place_id == place_id).limit(1)
    )
    return stored == PetPolicyType.NOT_ALLOWED
