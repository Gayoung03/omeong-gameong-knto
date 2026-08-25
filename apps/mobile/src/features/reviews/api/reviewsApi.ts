import { apiClient } from '@/src/services/apiClient';

import { toMyReviews, toReview, toReviewList } from './reviewAdapter';
import type { MyReview, Review, ReviewList } from '../types/review';
import type {
  MyReviewListResponse,
  ReviewCreatePayload,
  ReviewItemResponse,
  ReviewListResponse,
  ReviewSortOption,
  ReviewUpdatePayload,
} from '../types/reviewApi';

/** 서버 상한은 100 이다. 한 장소의 리뷰가 그보다 많아지면 페이지를 붙여야 한다. */
const DEFAULT_LIMIT = 20;

type ListOptions = {
  sort?: ReviewSortOption;
  limit?: number;
  offset?: number;
};

/**
 * 장소별 리뷰 목록.
 *
 * 로그인하지 않아도 볼 수 있다(서버가 인증을 '선택'으로 뒀다).
 * 다만 비로그인이면 모든 항목의 `isMine` 이 false 라 수정·삭제 메뉴가 안 뜬다.
 */
export async function fetchPlaceReviews(
  placeId: string,
  options: ListOptions = {},
): Promise<ReviewList> {
  const { data } = await apiClient.get<ReviewListResponse>(`/places/${placeId}/reviews`, {
    params: {
      limit: options.limit ?? DEFAULT_LIMIT,
      offset: options.offset ?? 0,
      sort: options.sort ?? 'recent',
    },
  });

  return toReviewList(data, placeId);
}

/**
 * 리뷰 작성.
 *
 * 같은 장소에 30일 안에 또 쓰면 서버가 **429** 를 준다. 고장이 아니라 규칙이라
 * 화면은 재시도를 권하지 않는다. 문구는 `getApiErrorMessage` 의 `rateLimit` 에 이미 있다.
 */
export async function createPlaceReview(
  placeId: string,
  payload: ReviewCreatePayload,
): Promise<Review> {
  const { data } = await apiClient.post<ReviewItemResponse>(`/places/${placeId}/reviews`, payload);

  return toReview(data, placeId);
}

/**
 * 리뷰 수정. 30일 제한은 새로 쓸 때만 걸리고 수정에는 없다.
 *
 * `placeId` 는 서버에 보내지 않는다 — 응답에 장소 id 가 없어서
 * 어댑터에 넘겨주기 위해서만 받는다.
 */
export async function updateReview(
  reviewId: string,
  placeId: string,
  payload: ReviewUpdatePayload,
): Promise<Review> {
  const { data } = await apiClient.patch<ReviewItemResponse>(`/reviews/${reviewId}`, payload);

  return toReview(data, placeId);
}

/**
 * 리뷰 삭제. **물리 삭제**라 되돌릴 수 없다(reviews 에 deleted_at 이 없다).
 * 사진도 CASCADE 로 함께 지워진다.
 */
export async function deleteReview(reviewId: string): Promise<void> {
  await apiClient.delete(`/reviews/${reviewId}`);
}

/** 내가 쓴 리뷰 목록. 최신순 고정이라 정렬 파라미터가 없다. */
export async function fetchMyReviews(
  options: Pick<ListOptions, 'limit' | 'offset'> = {},
): Promise<{ items: MyReview[]; total: number }> {
  const { data } = await apiClient.get<MyReviewListResponse>('/users/me/reviews', {
    params: {
      limit: options.limit ?? DEFAULT_LIMIT,
      offset: options.offset ?? 0,
    },
  });

  return { items: toMyReviews(data), total: data.total };
}
