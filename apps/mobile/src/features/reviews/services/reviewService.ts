import { getAuthSession } from '@/src/features/auth/services/authStorage';
import { createId } from '@/src/utils/createId';

import { mockReviews } from '../mocks/review.mock';
import type { Review } from '../types/review';

const FETCH_DELAY_MS = 300;
const UPLOAD_DELAY_MS = 400;
const MUTATION_DELAY_MS = 300;

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

/**
 * 세션 내 메모리 저장소.
 * TODO: 실제 API 연동 시 이 배열 접근을 apiClient 호출로 교체 (reviews 테이블)
 */
let currentReviews: Review[] = mockReviews.map((review) => ({ ...review }));

export type ReviewFormInput = {
  placeId: string;
  rating: number;
  content: string;
  /** 앨범에서 고른 로컬 이미지 URI 목록. 최대 3장. */
  localPhotoUris?: string[];
  petPolicyAccurate: boolean | null;
};

/** 최신 리뷰가 항상 맨 앞에 온다. TODO: 실제 API 연동 시 GET /places/{placeId}/reviews */
export async function fetchReviews(placeId: string): Promise<Review[]> {
  await wait(FETCH_DELAY_MS);
  return currentReviews
    .filter((review) => review.placeId === placeId)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

/** TODO: 실제 API 연동 시 이미지 업로드 API 호출 후 서버 URL 반환 */
export async function uploadReviewPhotos(localUris: string[]): Promise<string[]> {
  if (localUris.length === 0) return [];

  await wait(UPLOAD_DELAY_MS);
  return [...localUris];
}

/** TODO: 실제 API 연동 시 POST /places/{placeId}/reviews. id·작성자·createdAt은 서버가 발급한다. */
export async function createReview(input: ReviewFormInput): Promise<Review> {
  await wait(MUTATION_DELAY_MS);

  const session = await getAuthSession();

  const review: Review = {
    id: createId('review'),
    placeId: input.placeId,
    authorName: session?.nickname ?? '나',
    rating: input.rating,
    content: input.content,
    photoUrls: input.localPhotoUris ?? [],
    petPolicyAccurate: input.petPolicyAccurate,
    createdAt: new Date().toISOString(),
  };

  currentReviews = [review, ...currentReviews];
  return { ...review };
}
