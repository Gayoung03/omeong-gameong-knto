import type { MyReview, Review, ReviewList, ReviewSummary } from '../types/review';
import type {
  MyReviewListResponse,
  ReviewImageResponse,
  ReviewItemResponse,
  ReviewListResponse,
  ReviewSummaryResponse,
} from '../types/reviewApi';

/**
 * 사진은 `sortOrder` 가 곧 화면 순서다. 서버가 정렬해 내려주지만
 * 순서에 뜻이 있는 값이라 앱에서도 한 번 더 맞춘다.
 */
function toPhotoUrls(images: ReviewImageResponse[]): string[] {
  return [...images].sort((a, b) => a.sortOrder - b.sortOrder).map((image) => image.imageUrl);
}

/**
 * 서버 리뷰 한 건을 앱 타입으로 옮긴다.
 *
 * `placeId` 를 따로 받는 이유 — **서버 응답에 장소 id 가 없다.**
 * 장소별 목록 엔드포인트라 서버 쪽에서는 자명하지만, 앱은 이 값으로 캐시 키를 만든다.
 */
export function toReview(response: ReviewItemResponse, placeId: string): Review {
  return {
    authorAvatar: response.author.profileImageUrl ?? undefined,
    authorName: response.author.nickname,
    content: response.content ?? '',
    createdAt: response.createdAt,
    id: response.id,
    isEdited: response.isEdited,
    isMine: response.isMine,
    petName: response.pet?.name ?? null,
    petPolicyAccurate: response.petPolicyAccurate,
    photoUrls: toPhotoUrls(response.images),
    placeId,
    rating: response.rating,
    visitedAt: response.visitedAt,
  };
}

export function toReviewSummary(response: ReviewSummaryResponse): ReviewSummary {
  return {
    averageRating: response.averageRating,
    petPolicyAccurateRate: response.petPolicyAccurateRate,
    ratingDistribution: response.ratingDistribution,
    totalCount: response.totalCount,
  };
}

export function toReviewList(response: ReviewListResponse, placeId: string): ReviewList {
  return {
    items: response.items.map((item) => toReview(item, placeId)),
    summary: toReviewSummary(response.summary),
    total: response.total,
  };
}

/** 내가 쓴 리뷰는 장소 정보가 붙어 있어 목록 항목을 따로 편다. */
export function toMyReviews(response: MyReviewListResponse): MyReview[] {
  return response.items.map((item) => ({
    content: item.content ?? '',
    createdAt: item.createdAt,
    id: item.id,
    photoUrls: toPhotoUrls(item.images),
    placeId: item.place.id,
    placeImageUrl: item.place.primaryImageUrl,
    placeName: item.place.name,
    rating: item.rating,
    visitedAt: item.visitedAt,
  }));
}
