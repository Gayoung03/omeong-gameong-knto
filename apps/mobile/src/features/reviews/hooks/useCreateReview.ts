import { useMutation, useQueryClient } from '@tanstack/react-query';

import { invalidateReviewCaches } from './reviewCache';
import { uploadReviewPhotos } from '../api/reviewPhotos';
import { createPlaceReview } from '../api/reviewsApi';
import type { Review } from '../types/review';

export type ReviewFormInput = {
  placeId: string;
  rating: number;
  content: string;
  /** 앨범에서 고른 로컬 이미지 URI 목록. 최대 3장. */
  localPhotoUris?: string[];
  petPolicyAccurate: boolean | null;
  /** 함께 간 반려동물. 화면에 선택 UI 가 아직 없어 지금은 항상 비어 있다. */
  petId?: string | null;
  /** 방문일(YYYY-MM-DD). 화면에 입력 칸이 아직 없다. */
  visitedAt?: string | null;
};

export function useCreateReview() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: ReviewFormInput): Promise<Review> => {
      // 업로드가 실패하면 리뷰 자체를 만들지 않아 사용자가 그대로 재시도할 수 있다.
      const imageUrls = await uploadReviewPhotos(input.localPhotoUris ?? []);

      return createPlaceReview(input.placeId, {
        // 서버는 빈 문자열도 받지만 "안 썼다"와 구분되지 않아 null 로 보낸다.
        content: input.content.trim() || null,
        imageUrls,
        petId: input.petId ?? null,
        petPolicyAccurate: input.petPolicyAccurate,
        rating: input.rating,
        visitedAt: input.visitedAt ?? null,
      });
    },
    onSuccess: (created) => {
      // 새 리뷰를 캐시 앞에 끼워 넣지 않고 다시 받아온다.
      // 평균 별점·분포는 서버가 세는 값이라 앱에서 흉내 내면 어긋난다.
      invalidateReviewCaches(queryClient, created.placeId);
    },
  });
}
