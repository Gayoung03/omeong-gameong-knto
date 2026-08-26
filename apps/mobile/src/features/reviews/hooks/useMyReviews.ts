import { useQuery } from '@tanstack/react-query';

import { reviewQueryKeys } from './useReviews';
import { fetchMyReviews } from '../api/reviewsApi';

/** 내가 쓴 리뷰. 로그인한 사용자만 부를 수 있다(서버가 401 을 준다). */
export function useMyReviews() {
  return useQuery({
    queryFn: () => fetchMyReviews(),
    queryKey: reviewQueryKeys.mine(),
  });
}
