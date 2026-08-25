import type { QueryClient } from '@tanstack/react-query';

import { placeDetailQueryKey } from '@/src/features/places/hooks/usePlaceDetail';
import { placesQueryKey } from '@/src/features/places/hooks/usePlaces';

import { reviewQueryKeys } from './useReviews';

/**
 * 리뷰가 바뀌면 장소 쪽 캐시도 함께 낡는다.
 *
 * 장소의 평점·리뷰수는 저장된 값이 아니라 **조회할 때마다 세는 집계**다.
 * 그래서 리뷰를 하나 쓰거나 지우면 리뷰 목록만이 아니라
 * 장소 목록·상세의 숫자까지 동시에 달라진다. 한 곳에 모아둬야 빠뜨리지 않는다.
 */
export function invalidateReviewCaches(queryClient: QueryClient, placeId: string): void {
  queryClient.invalidateQueries({ queryKey: reviewQueryKeys.list(placeId) });
  queryClient.invalidateQueries({ queryKey: reviewQueryKeys.mine() });
  queryClient.invalidateQueries({ queryKey: placeDetailQueryKey(placeId) });
  queryClient.invalidateQueries({ queryKey: placesQueryKey });
}
