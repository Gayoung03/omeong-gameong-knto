import type { PetPolicy } from '@/src/types/place';

/**
 * 장소 상세 화면이 보는 단일 모델.
 *
 * 지금 장소 데이터는 두 벌로 나뉘어 있고 서로 가진 필드가 다르다.
 * - `places` 목데이터: 지역 · 실내/야외 · 거리 · 동반 가능 여부
 * - `trips` 목데이터: 설명 · 동반 정책 · 평점 · 리뷰수 · 저장수 · 예약 가능
 *
 * 어느 쪽에서 왔든 이 타입 하나로 맞춰서 화면에 넘긴다.
 * 상대에게 없는 값은 `null` 이고, 화면은 `null` 인 항목을 그리지 않는다.
 */
export type PlaceDetail = {
  id: string;
  name: string;
  address: string;
  /** 화면에 그대로 보여줄 분류 문구 */
  categoryLabel: string;
  imageUrl: string | null;
  latitude: number;
  longitude: number;
  description: string | null;
  petPolicy: PetPolicy | null;
  /** 동반 정책까지는 모르고 가능 여부만 아는 경우 */
  petFriendly: boolean | null;
  rating: number | null;
  reviewCount: number | null;
  savedCount: number | null;
  region: string | null;
  environment: '실내' | '야외' | null;
  distanceKm: number | null;
  isReservable: boolean | null;
  /** 어느 목데이터에서 왔는지. API 연동 전까지만 쓰는 값 */
  source: 'places' | 'trips';
};
