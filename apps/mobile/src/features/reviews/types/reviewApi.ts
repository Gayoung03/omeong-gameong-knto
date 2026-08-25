/**
 * 리뷰 API 응답·요청 타입.
 *
 * 서버 스키마가 `to_camel` 별칭이라 키는 camelCase 지만 **enum 값은 snake_case** 다
 * (`dog`·`small`). 앱 쪽 반려동물 타입은 한글 union 이라 그대로 못 쓴다.
 *
 * 주의 — `ReviewItemResponse` 에는 **`placeId` 가 없다.** 장소별 목록 엔드포인트라
 * 서버 쪽에서는 자명하지만, 앱은 그 값으로 캐시 키를 만든다.
 * 그래서 어댑터가 요청에 쓴 placeId 를 따로 받는다.
 */

export type ReviewApiSpecies = 'dog' | 'cat' | 'other';
export type ReviewApiSize = 'small' | 'medium' | 'large';

/** 서버 `sort` 파라미터 값. 기본은 recent. */
export type ReviewSortOption = 'recent' | 'ratingHigh' | 'ratingLow';

export type ReviewAuthorResponse = {
  /** 탈퇴한 사용자는 서버가 '탈퇴한 사용자' 로 바꿔서 내린다. 사용자 id 는 내리지 않는다. */
  nickname: string;
  profileImageUrl: string | null;
};

export type ReviewPetResponse = {
  name: string;
  species: ReviewApiSpecies;
  speciesDetail: string | null;
  size: ReviewApiSize | null;
};

export type ReviewImageResponse = {
  imageUrl: string;
  sortOrder: number;
};

export type ReviewItemResponse = {
  id: string;
  rating: number;
  content: string | null;
  petPolicyAccurate: boolean | null;
  /** **날짜**(YYYY-MM-DD)다. travelLog 의 visitedAt 은 시각이라 형식이 다르다. */
  visitedAt: string | null;
  images: ReviewImageResponse[];
  author: ReviewAuthorResponse;
  pet: ReviewPetResponse | null;
  /** 보고 있는 사람이 쓴 리뷰인지. 비로그인이면 언제나 false */
  isMine: boolean;
  isEdited: boolean;
  createdAt: string;
  updatedAt: string;
};

/** 별점 분포는 키가 별점 문자열이다. `{"5": 20, "4": 10, ...}` */
export type ReviewSummaryResponse = {
  averageRating: number | null;
  totalCount: number;
  ratingDistribution: Record<string, number>;
  petPolicyAccurateRate: number | null;
};

export type ReviewListResponse = {
  items: ReviewItemResponse[];
  total: number;
  limit: number;
  offset: number;
  summary: ReviewSummaryResponse;
};

export type ReviewPlaceSummaryResponse = {
  id: string;
  name: string;
  primaryImageUrl: string | null;
};

/** 내가 쓴 리뷰. 작성자가 나인 게 자명해서 `author` 가 빠지고 `place` 가 붙는다. */
export type MyReviewItemResponse = {
  id: string;
  rating: number;
  content: string | null;
  visitedAt: string | null;
  images: ReviewImageResponse[];
  place: ReviewPlaceSummaryResponse;
  createdAt: string;
};

export type MyReviewListResponse = {
  items: MyReviewItemResponse[];
  total: number;
  limit: number;
  offset: number;
};

export type ReviewCreatePayload = {
  rating: number;
  content: string | null;
  petPolicyAccurate: boolean | null;
  visitedAt?: string | null;
  petId?: string | null;
  /** 배열 순서가 그대로 `review_images.sort_order` 가 된다. */
  imageUrls: string[];
};

/**
 * 보낸 필드만 고친다.
 *
 * `imageUrls` 를 보내면 **기존 이미지를 전부 지우고 새로 저장**한다.
 * 개별 이미지만 빼는 방법은 없다 — 화면이 항상 전체 목록을 제출하기 때문이다.
 * `placeId` 와 `petId` 는 못 바꾼다.
 */
export type ReviewUpdatePayload = {
  rating?: number;
  content?: string | null;
  petPolicyAccurate?: boolean | null;
  visitedAt?: string | null;
  imageUrls?: string[];
};
