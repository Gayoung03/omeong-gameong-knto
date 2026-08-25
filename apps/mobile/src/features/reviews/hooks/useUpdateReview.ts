import { useMutation, useQueryClient } from '@tanstack/react-query';

import { invalidateReviewCaches } from './reviewCache';
import { uploadReviewPhotos } from '../api/reviewPhotos';
import { updateReview } from '../api/reviewsApi';
import type { Review } from '../types/review';

export type ReviewEditInput = {
  reviewId: string;
  placeId: string;
  rating: number;
  content: string;
  /**
   * 화면에 남아 있는 사진 전체.
   * 기존 서버 URL 과 새로 고른 로컬 URI 가 섞여 있고, 업로드 단계가 구분한다.
   */
  photoUris: string[];
  petPolicyAccurate: boolean | null;
};

/**
 * 리뷰 수정.
 *
 * 사진은 **전체 목록을 다시 보낸다.** 서버가 받은 배열로 통째로 갈아끼우는 방식이라
 * 한 장만 빼려 해도 남길 것들을 모두 담아 보내야 한다.
 */
export function useUpdateReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: ReviewEditInput): Promise<Review> => {
      const imageUrls = await uploadReviewPhotos(input.photoUris);

      return updateReview(input.reviewId, input.placeId, {
        content: input.content.trim() || null,
        imageUrls,
        petPolicyAccurate: input.petPolicyAccurate,
        rating: input.rating,
      });
    },
    onSuccess: (updated) => {
      invalidateReviewCaches(queryClient, updated.placeId);
    },
  });
}
