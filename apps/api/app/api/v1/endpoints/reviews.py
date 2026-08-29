"""장소 리뷰 엔드포인트.

리뷰는 **물리 삭제**다. reviews 에 deleted_at 이 없어서 users·pets 와 달리
soft delete 대상이 아니다. 그래서 응답에 status 필드도 없다.
"""

import uuid
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Float, case, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser, OptionalUser
from app.db.models import Pet, Place, Review, ReviewImage, User
from app.db.session import get_db
from app.schemas.review import (
    MyReviewItem,
    MyReviewListResponse,
    ReviewAuthor,
    ReviewCreate,
    ReviewImageResponse,
    ReviewItem,
    ReviewListResponse,
    ReviewPet,
    ReviewPlaceSummary,
    ReviewSummary,
    ReviewUpdate,
)
from app.services.place_access import load_visible_place

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

#: 같은 장소에 다시 쓰려면 이만큼 지나야 한다. "한 달"이 아니라 30일 고정이다 —
#: 달마다 일수가 달라 생기는 예외를 없애기 위해서다(docs/api/reviews.md).
REWRITE_INTERVAL = timedelta(days=30)
REWRITE_BLOCKED_MESSAGE = "동일 장소 리뷰는 한 달에 한번만 가능해요"

#: 탈퇴한 사용자의 리뷰는 남기고 작성자만 익명으로 바꾼다. 리뷰를 함께 지우면
#: 별점 평균이 흔들린다 — 리뷰는 쓴 사람의 것이면서 남이 보는 공용 정보다.
WITHDRAWN_NICKNAME = "탈퇴한 사용자"

#: 방문일 검증은 한국 날짜로 한다. 컨테이너는 UTC 로 도는데 그대로 쓰면
#: 한국 시각 오전 9시 전에 '오늘' 방문했다고 보낸 리뷰가 미래로 판정된다.
KST = timezone(timedelta(hours=9))


class ReviewSort(StrEnum):
    RECENT = "recent"
    RATING_HIGH = "ratingHigh"
    RATING_LOW = "ratingLow"


@router.get(
    "/places/{place_id}/reviews", response_model=ReviewListResponse, summary="장소별 리뷰 목록"
)
def list_place_reviews(
    place_id: uuid.UUID,
    current_user: OptionalUser,
    db: DbSession,
    sort: ReviewSort = ReviewSort.RECENT,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReviewListResponse:
    # 남의 개인 장소의 리뷰는 남에게 보이지 않는다(장소 조회와 동일 규칙).
    load_visible_place(db, place_id, current_user)

    condition = Review.place_id == place_id
    total = db.scalar(select(func.count(Review.id)).where(condition)) or 0

    statement = (
        select(Review)
        .where(condition)
        # 리뷰 한 건마다 이미지·작성자·반려동물을 따로 읽으면 20건에 60번 왕복한다.
        .options(
            selectinload(Review.images),
            selectinload(Review.author),
            selectinload(Review.pet),
        )
    )
    if sort is ReviewSort.RATING_HIGH:
        statement = statement.order_by(Review.rating.desc(), Review.created_at.desc())
    elif sort is ReviewSort.RATING_LOW:
        statement = statement.order_by(Review.rating, Review.created_at.desc())
    else:
        statement = statement.order_by(Review.created_at.desc())

    reviews = db.scalars(statement.limit(limit).offset(offset)).all()

    return ReviewListResponse(
        items=[_to_item(review, current_user) for review in reviews],
        total=total,
        limit=limit,
        offset=offset,
        summary=_summary_of(db, place_id),
    )


@router.post(
    "/places/{place_id}/reviews",
    response_model=ReviewItem,
    status_code=status.HTTP_201_CREATED,
    summary="리뷰 작성",
)
def create_review(
    place_id: uuid.UUID,
    payload: ReviewCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ReviewItem:
    # 남의 개인 장소에는 리뷰를 쓸 수 없다(장소 조회와 동일 규칙).
    load_visible_place(db, place_id, current_user)

    if payload.visited_at and payload.visited_at > datetime.now(KST).date():
        raise HTTPException(status_code=422, detail="방문일은 미래일 수 없습니다")

    if payload.pet_id is not None:
        pet = db.get(Pet, payload.pet_id)
        if pet is None:
            raise HTTPException(status_code=404, detail="반려동물을 찾을 수 없습니다")
        # 삭제된 반려동물도 지정할 수 있다. 소유자만 확인한다.
        if pet.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="다른 사용자의 반려동물입니다")

    _guard_rewrite_interval(db, place_id, current_user)

    review = Review(
        user_id=current_user.id,
        place_id=place_id,
        pet_id=payload.pet_id,
        rating=payload.rating,
        content=payload.content,
        pet_policy_accurate=payload.pet_policy_accurate,
        visited_at=payload.visited_at,
    )
    db.add(review)
    db.flush()
    _replace_images(db, review, payload.image_urls)

    db.commit()
    db.refresh(review)
    return _to_item(review, current_user)


@router.get("/users/me/reviews", response_model=MyReviewListResponse, summary="내가 쓴 리뷰")
def list_my_reviews(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MyReviewListResponse:
    condition = Review.user_id == current_user.id
    total = db.scalar(select(func.count(Review.id)).where(condition)) or 0

    rows = db.execute(
        select(Review, Place)
        .join(Place, Place.id == Review.place_id)
        .where(condition)
        .options(selectinload(Review.images))
        .order_by(Review.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return MyReviewListResponse(
        items=[
            MyReviewItem(
                id=review.id,
                rating=review.rating,
                content=review.content,
                visited_at=review.visited_at,
                images=_images_of(review),
                place=ReviewPlaceSummary(
                    id=place.id, name=place.name, primary_image_url=place.primary_image_url
                ),
                created_at=review.created_at,
            )
            for review, place in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/reviews/{review_id}", response_model=ReviewItem, summary="리뷰 수정")
def update_review(
    review_id: uuid.UUID,
    payload: ReviewUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ReviewItem:
    """수정에는 기간 제한이 없다. 30일 제한은 새 리뷰를 쓸 때만 적용된다."""
    review = _load_own_review(db, review_id, current_user)

    changes = payload.model_dump(exclude_unset=True)
    image_urls = changes.pop("image_urls", None)

    if changes.get("visited_at") and changes["visited_at"] > datetime.now(KST).date():
        raise HTTPException(status_code=422, detail="방문일은 미래일 수 없습니다")

    for field, value in changes.items():
        setattr(review, field, value)

    if image_urls is not None:
        _replace_images(db, review, image_urls)

    db.commit()
    db.refresh(review)
    return _to_item(review, current_user)


@router.delete(
    "/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT, summary="리뷰 삭제"
)
def delete_review(review_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> Response:
    """물리 삭제다. review_images 도 ON DELETE CASCADE 로 함께 지워진다.

    장소의 reviewCount·rating 은 저장된 값이 아니라 조회 시 집계라
    따로 갱신할 것이 없다.
    """
    review = _load_own_review(db, review_id, current_user)
    db.delete(review)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 공용
# ---------------------------------------------------------------------------


def _load_own_review(db: Session, review_id: uuid.UUID, user: User) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")
    if review.user_id != user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 리뷰입니다")
    return review


def _guard_rewrite_interval(db: Session, place_id: uuid.UUID, user: User) -> None:
    """같은 장소에 30일 안에 또 쓰면 429.

    재방문 후기는 남길 수 있게 하되, 한 사람이 같은 장소의 평점을 여러 번
    올리거나 내리는 것을 막는다. 기존 인덱스(user_id, created_at)를 그대로 쓴다.
    """
    latest = db.scalar(
        select(func.max(Review.created_at)).where(
            Review.user_id == user.id, Review.place_id == place_id
        )
    )
    if latest is None:
        return

    if datetime.now(UTC) - latest < REWRITE_INTERVAL:
        raise HTTPException(status_code=429, detail=REWRITE_BLOCKED_MESSAGE)


def _replace_images(db: Session, review: Review, image_urls: list[str]) -> None:
    """이미지를 통째로 갈아끼운다.

    (review_id, sort_order) 에 UNIQUE 가 있어 남겨둔 채 새로 넣으면 부딪친다.
    지우고 flush 한 뒤에 넣는다.
    """
    for existing in list(review.images):
        db.delete(existing)
    db.flush()

    for order, url in enumerate(image_urls):
        db.add(ReviewImage(review_id=review.id, image_url=url, sort_order=order))
    db.flush()


def _images_of(review: Review) -> list[ReviewImageResponse]:
    return [
        ReviewImageResponse(image_url=image.image_url, sort_order=image.sort_order)
        for image in sorted(review.images, key=lambda image: image.sort_order)
    ]


def _to_item(review: Review, viewer: User | None) -> ReviewItem:
    author = review.author
    withdrawn = author is None or author.deleted_at is not None

    return ReviewItem(
        id=review.id,
        rating=review.rating,
        content=review.content,
        pet_policy_accurate=review.pet_policy_accurate,
        visited_at=review.visited_at,
        images=_images_of(review),
        author=ReviewAuthor(
            nickname=WITHDRAWN_NICKNAME if withdrawn else author.nickname,
            profile_image_url=None if withdrawn else author.profile_image_url,
        ),
        pet=(
            None
            if review.pet is None
            else ReviewPet(
                name=review.pet.name,
                species=review.pet.species,
                species_detail=review.pet.species_detail,
                size=review.pet.size,
            )
        ),
        is_mine=viewer is not None and review.user_id == viewer.id,
        # 작성 시점에는 created_at 과 updated_at 이 같은 트랜잭션의 now() 라
        # 정확히 같은 값이다. 오판이 생기지 않는다.
        is_edited=review.updated_at > review.created_at,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _summary_of(db: Session, place_id: uuid.UUID) -> ReviewSummary:
    condition = Review.place_id == place_id

    distribution = {
        str(score): count
        for score, count in db.execute(
            select(Review.rating, func.count(Review.id)).where(condition).group_by(Review.rating)
        ).all()
    }
    total = sum(distribution.values())

    average = db.scalar(select(func.avg(Review.rating)).where(condition))
    # PostgreSQL 은 boolean 을 숫자로 바로 캐스팅하지 못한다. CASE 로 1/0 을 만든다.
    accurate_rate = db.scalar(
        select(func.avg(case((Review.pet_policy_accurate.is_(True), 1.0), else_=0.0).cast(Float)))
        .where(condition)
        .where(Review.pet_policy_accurate.is_not(None))
    )

    return ReviewSummary(
        average_rating=round(float(average), 1) if average is not None else None,
        total_count=total,
        # 별점 하나도 빠뜨리지 않고 0 으로 채운다. 화면이 5~1 막대를 항상 그린다.
        rating_distribution={
            str(score): distribution.get(str(score), 0) for score in range(5, 0, -1)
        },
        pet_policy_accurate_rate=(
            round(float(accurate_rate), 2) if accurate_rate is not None else None
        ),
    )
