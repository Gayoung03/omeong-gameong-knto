/**
 * 장소 리뷰 하나. 서버 `ReviewItem` 을 화면이 쓰기 좋은 모양으로 옮긴 것이다.
 * 변환은 `api/reviewAdapter.ts` 한 곳에서만 한다.
 */
export type Review = {
  id: string;
  /** 서버 응답에는 없다. 어댑터가 요청에 쓴 값을 넣는다(`types/reviewApi.ts` 참고). */
  placeId: string;
  authorName: string;
  authorAvatar?: string;
  rating: number;
  /** 서버는 내용 없는 별점만 리뷰도 허용한다. 없으면 빈 문자열이고 화면이 안 그린다. */
  content: string;
  photoUrls: string[];
  /** 동반정책 정보가 실제와 맞았는지. 응답하지 않았으면 null */
  petPolicyAccurate: boolean | null;
  createdAt: string;
  /** 내가 쓴 리뷰인지. 수정·삭제 메뉴는 이 값이 true 일 때만 보인다. */
  isMine: boolean;
  /** 작성 뒤 한 번이라도 고쳤는지. 서버가 `updatedAt > createdAt` 으로 판단한다. */
  isEdited: boolean;
  /** 방문일. **날짜**(YYYY-MM-DD)다 — travelLog 의 visitedAt 은 시각이라 다르다. */
  visitedAt: string | null;
  /** 함께 간 반려동물 이름. 지정하지 않았으면 null */
  petName: string | null;
};

/**
 * 장소 하나의 리뷰 집계. 서버가 목록 응답에 함께 담아준다.
 *
 * **목록 길이로 개수를 세면 안 된다.** 목록은 한 번에 20건씩 오는 페이지라
 * 21번째부터는 빠진다. 개수는 언제나 `totalCount` 를 쓴다.
 */
export type ReviewSummary = {
  averageRating: number | null;
  totalCount: number;
  /** 키가 별점 문자열이다. `{"5": 20, "4": 10, ...}` */
  ratingDistribution: Record<string, number>;
  /** 동반정책이 정확했다고 답한 비율. 0~1. 응답이 하나도 없으면 null */
  petPolicyAccurateRate: number | null;
};

export type ReviewList = {
  items: Review[];
  total: number;
  summary: ReviewSummary;
};

/**
 * 내가 쓴 리뷰. 장소별 목록과 응답 모양이 다르다 —
 * 작성자가 빠지고 어느 장소에 썼는지가 붙는다.
 */
export type MyReview = {
  id: string;
  rating: number;
  content: string;
  photoUrls: string[];
  visitedAt: string | null;
  createdAt: string;
  placeId: string;
  placeName: string;
  placeImageUrl: string | null;
};

/** 목록을 아직 못 받았을 때 화면이 0으로 그릴 수 있게 두는 기본값. */
export const EMPTY_REVIEW_SUMMARY: ReviewSummary = {
  averageRating: null,
  petPolicyAccurateRate: null,
  ratingDistribution: {},
  totalCount: 0,
};

export const REVIEW_CONTENT_MAX_LENGTH = 100;
export const REVIEW_PHOTO_MAX_COUNT = 3;
export const REVIEW_RATING_MIN = 1;
export const REVIEW_RATING_MAX = 5;
