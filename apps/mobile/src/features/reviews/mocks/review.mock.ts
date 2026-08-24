import type { Review } from '../types/review';

/**
 * 장소별 리뷰 목업.
 * place.mock.ts 의 id 와 맞춰뒀다. 상단 요약(⭐평점·리뷰수)은 place 목업의 고정값을
 * 그대로 쓰고 있어 이 배열의 개수와는 맞지 않을 수 있다 — 실제 API가 붙으면 자연히 해결된다.
 *
 * TODO: 실제 API 연동 시 이 배열을 GET /places/{placeId}/reviews 호출로 교체한다.
 */
export const mockReviews: Review[] = [
  {
    id: 'review-hamdeok-1',
    placeId: 'hamdeok-beach',
    authorName: '제주여행자',
    rating: 5,
    content: '백사장이 넓어서 강아지랑 뛰어놀기 정말 좋았어요. 리드줄만 하면 문제없어요.',
    photoUrls: [],
    petPolicyAccurate: true,
    createdAt: '2026-07-02T09:12:00+09:00',
  },
  {
    id: 'review-hamdeok-2',
    placeId: 'hamdeok-beach',
    authorName: '몽이맘',
    rating: 4,
    content: '주말엔 사람이 많아서 조금 붐벼요. 평일 오전 추천!',
    photoUrls: [],
    petPolicyAccurate: null,
    createdAt: '2026-06-18T14:30:00+09:00',
  },
  {
    id: 'review-delmoondo-1',
    placeId: 'delmoondo',
    authorName: '코코보호자',
    rating: 3,
    content: '실내는 동반 가능한데 좌석이 좁아서 대형견은 좀 불편할 수 있어요.',
    photoUrls: [],
    petPolicyAccurate: false,
    createdAt: '2026-07-10T11:00:00+09:00',
  },
];
