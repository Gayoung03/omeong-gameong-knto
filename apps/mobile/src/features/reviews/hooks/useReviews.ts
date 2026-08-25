import { useQuery } from '@tanstack/react-query';

import { fetchPlaceReviews } from '../api/reviewsApi';
import type { ReviewList } from '../types/review';

export const reviewQueryKeys = {
  /** 리뷰 관련 캐시 전체. 목록·내 리뷰를 한 번에 무효화할 때 쓴다. */
  all: () => ['reviews'] as const,
  list: (placeId: string) => ['reviews', 'list', placeId] as const,
  mine: () => ['reviews', 'mine'] as const,
};

/**
 * 장소 하나의 리뷰 목록과 집계.
 *
 * 집계(`summary`)가 목록과 같은 응답에 들어 있어 요청이 한 번이다.
 * 평균 별점·총 개수는 반드시 `summary` 를 쓴다 — `items.length` 는 한 페이지 길이다.
 */
export function useReviews(placeId: string) {
  return useQuery<ReviewList>({
    enabled: placeId.length > 0,
    queryFn: () => fetchPlaceReviews(placeId),
    queryKey: reviewQueryKeys.list(placeId),
  });
}
