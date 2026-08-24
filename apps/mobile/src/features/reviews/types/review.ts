/**
 * 장소 리뷰 하나.
 *
 * DB의 reviews 테이블은 user_id 만 갖고 작성자 이름은 저장하지 않는다.
 * 실제로는 사용자 테이블과 join 해서 채우는 값이라, API 연동 전까지는
 * authorName 을 화면이 바로 쓸 수 있는 형태로 넣어둔다.
 * TODO: 실제 API 연동 시 서버 응답의 user 정보로 authorName·authorAvatar 를 채운다.
 */
export type Review = {
  id: string;
  placeId: string;
  authorName: string;
  authorAvatar?: string;
  rating: number;
  content: string;
  photoUrls: string[];
  /** 동반정책 정보가 실제와 맞았는지. 응답하지 않으면 null */
  petPolicyAccurate: boolean | null;
  createdAt: string;
};

export const REVIEW_CONTENT_MAX_LENGTH = 100;
export const REVIEW_PHOTO_MAX_COUNT = 3;
export const REVIEW_RATING_MIN = 1;
export const REVIEW_RATING_MAX = 5;
