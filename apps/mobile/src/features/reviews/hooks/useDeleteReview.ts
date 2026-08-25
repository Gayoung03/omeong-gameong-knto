import { useMutation, useQueryClient } from '@tanstack/react-query';

import { invalidateReviewCaches } from './reviewCache';
import { deleteReview } from '../api/reviewsApi';

export type ReviewDeleteInput = {
  reviewId: string;
  /** 삭제 뒤 어느 장소의 캐시를 새로 받을지 정하는 데 쓴다. */
  placeId: string;
};

/**
 * 리뷰 삭제.
 *
 * **되돌릴 수 없다.** reviews 테이블에 deleted_at 이 없어 물리 삭제이고
 * 사진도 함께 지워진다. 그래서 화면은 반드시 확인 모달을 거친다.
 */
export function useDeleteReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: ReviewDeleteInput): Promise<ReviewDeleteInput> => {
      await deleteReview(input.reviewId);
      return input;
    },
    onSuccess: ({ placeId }) => {
      invalidateReviewCaches(queryClient, placeId);
    },
  });
}
