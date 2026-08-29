"""반려동물 생성 도메인 로직.

## 왜 서비스로 뺐나

가입(`POST /auth/signup`)은 계정·반려동물·여행취향을 **한 트랜잭션**으로 저장한다
(docs/api/auth.md). "첫 활성 펫이 자동으로 대표가 된다"는 규칙이 `endpoints/pets.py`
안에 인라인으로 있으면, 가입이 같은 규칙을 복붙해 규칙이 두 벌이 된다. 한쪽만
고치면 등록 경로와 가입 경로가 어긋난다.

그래서 규칙을 여기 한 곳에 두고 **`add`+`flush` 까지만** 한다. `commit`(트랜잭션
경계)은 호출자가 갖는다 — 등록 엔드포인트는 자기 요청을 커밋하고, 가입은 계정·펫·
취향을 한 번에 커밋한다.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Pet
from app.schemas.pet import PetCreate


def create_pet(db: Session, user_id: uuid.UUID, payload: PetCreate) -> Pet:
    """반려동물 한 마리를 만든다. **첫 활성 펫이면 대표(`is_primary=True`)로 둔다.**

    이미 활성 펫이 있으면 새 펫은 대표가 아니다. 대표 판정은 "활성"만 센다 —
    삭제된(soft delete) 펫은 대표 자리를 차지하지 않는다(`endpoints/pets.py` 삭제
    로직과 짝을 이룬다).

    `add`+`flush` 까지만 하고 **commit 하지 않는다.** 트랜잭션 경계는 호출자 몫.
    """
    has_active_pet = db.scalar(
        select(Pet.id).where(Pet.user_id == user_id, Pet.deleted_at.is_(None)).limit(1)
    )
    pet = Pet(
        user_id=user_id,
        is_primary=has_active_pet is None,
        **payload.model_dump(),
    )
    db.add(pet)
    db.flush()
    return pet
