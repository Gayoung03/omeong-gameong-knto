import { useQuery } from '@tanstack/react-query';

import { fetchReviews } from '../services/reviewService';
import type { Review } from '../types/review';

export function reviewsQueryKey(placeId: string) {
  return ['reviews', 'list', placeId] as const;
}

export function useReviews(placeId: string) {
  return useQuery<Review[]>({
    enabled: placeId.length > 0,
    queryFn: () => fetchReviews(placeId),
    queryKey: reviewsQueryKey(placeId),
  });
}
