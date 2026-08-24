import { useMutation, useQueryClient } from '@tanstack/react-query';

import { reviewsQueryKey } from './useReviews';
import { createReview, uploadReviewPhotos, type ReviewFormInput } from '../services/reviewService';
import type { Review } from '../types/review';

export function useCreateReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: ReviewFormInput): Promise<Review> => {
      // 업로드가 실패하면 등록 자체를 진행하지 않아 사용자가 그대로 재시도할 수 있다.
      const uploadedUrls = await uploadReviewPhotos(input.localPhotoUris ?? []);

      return createReview({ ...input, localPhotoUris: uploadedUrls });
    },
    onSuccess: (created) => {
      // 목록은 최신순이라 새 리뷰가 항상 맨 앞에 온다.
      queryClient.setQueryData<Review[]>(reviewsQueryKey(created.placeId), (current = []) => [
        created,
        ...current,
      ]);
    },
  });
}
