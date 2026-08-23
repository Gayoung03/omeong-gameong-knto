"""리뷰 API 스키마.

`isMine` `isEdited` `summary` 는 계산값이라 엔드포인트가 채운다.
`visitedAt` 은 **날짜**다 — 같은 이름이지만 travel_logs.visited_at 은 시각이라
앱에서 같은 형식으로 다루면 안 된다(docs/api/reviews.md).
"""

import uuid
from datetime import date, datetime

from pydantic import Field

from app.db.models.enums import PetSize, PetSpecies
from app.schemas.base import APISchema


class ReviewAuthor(APISchema):
    """작성자. **사용자 id 는 내리지 않는다.**"""

    nickname: str
    profile_image_url: str | None


class ReviewPet(APISchema):
    name: str
    species: PetSpecies
    species_detail: str | None
    size: PetSize | None


class ReviewImageResponse(APISchema):
    image_url: str
    sort_order: int


class ReviewItem(APISchema):
    id: uuid.UUID
    rating: int
    content: str | None
    pet_policy_accurate: bool | None
    visited_at: date | None
    images: list[ReviewImageResponse]
    author: ReviewAuthor
    pet: ReviewPet | None
    is_mine: bool
    is_edited: bool
    created_at: datetime
    updated_at: datetime


class ReviewSummary(APISchema):
    """목록 응답에 함께 담는다. 화면이 별점 분포까지 한 번에 그린다."""

    average_rating: float | None
    total_count: int
    #: {"5": 20, "4": 10, ...} — 키가 별점, 값이 개수.
    rating_distribution: dict[str, int]
    pet_policy_accurate_rate: float | None


class ReviewListResponse(APISchema):
    items: list[ReviewItem]
    total: int
    limit: int
    offset: int
    summary: ReviewSummary


class ReviewPlaceSummary(APISchema):
    id: uuid.UUID
    name: str
    primary_image_url: str | None


class MyReviewItem(APISchema):
    """내가 쓴 리뷰. 작성자가 나인 게 자명해서 `author` 가 빠지고 `place` 가 붙는다."""

    id: uuid.UUID
    rating: int
    content: str | None
    visited_at: date | None
    images: list[ReviewImageResponse]
    place: ReviewPlaceSummary
    created_at: datetime


class MyReviewListResponse(APISchema):
    items: list[MyReviewItem]
    total: int
    limit: int
    offset: int


class ReviewCreate(APISchema):
    rating: int = Field(ge=1, le=5)
    content: str | None = None
    pet_policy_accurate: bool | None = None
    visited_at: date | None = None
    pet_id: uuid.UUID | None = None
    #: 배열 순서가 그대로 review_images.sort_order 가 된다.
    image_urls: list[str] = Field(default_factory=list)


class ReviewUpdate(APISchema):
    """보낸 필드만 수정한다.

    `imageUrls` 를 보내면 **기존 이미지를 전부 지우고 새로 저장**한다.
    개별 이미지만 빼는 방식은 없다 — 화면이 항상 전체 목록을 제출하기 때문이다.
    `placeId` 와 `petId` 는 못 바꾼다.
    """

    rating: int | None = Field(default=None, ge=1, le=5)
    content: str | None = None
    pet_policy_accurate: bool | None = None
    visited_at: date | None = None
    image_urls: list[str] | None = None
