import type { PlaceRegion } from '@/src/features/places/types/place';

/** 저장한 장소 한 건. 목록에 필요한 값만 복사해 둔다. */
export type SavedPlace = {
  id: string;
  name: string;
  address: string;
  category: string;
  /**
   * 지역 칩이 이걸로 거른다.
   *
   * 서버 지역명을 권역 6종에 못 맞추면 null 이다(`places/api/placeAdapter.ts` 의
   * `toRegion` 참고). 그 장소는 '전체' 에서만 보인다 — 장소 탐색과 같은 규칙이다.
   */
  region: PlaceRegion | null;
  /** 사진이 없는 장소가 있다. RemoteImage 가 플레이스홀더를 그린다. */
  imageUrl: string | null;
  /** ISO 8601. 목록을 최신순으로 정렬할 때 쓴다. */
  savedAt: string;
};

export type SavedRoutePlace = {
  id: string;
  name: string;
  order: number;
  time: string;
};

export type SavedRouteDay = {
  day: number;
  date: string;
  places: SavedRoutePlace[];
};

/**
 * 저장한 코스 한 건.
 *
 * 내부 용어는 가이드 11장의 `route`(AI 추천 경로)를 쓰고,
 * 화면에 보이는 문구만 "코스"로 둔다.
 */
export type SavedRoute = {
  id: string;
  title: string;
  petName: string;
  duration: string;
  startAt?: string;
  endAt?: string;
  placeCount: number;
  days: SavedRouteDay[];
  savedAt: string;
};
