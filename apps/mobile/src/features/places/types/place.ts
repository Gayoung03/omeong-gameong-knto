import type Ionicons from '@expo/vector-icons/Ionicons';
import type { ComponentProps } from 'react';

import type { PetPolicy } from '@/src/types/place';

export type PlaceIconName = ComponentProps<typeof Ionicons>['name'];

export type PlaceRegion =
  | '제주시/제주국제공항'
  | '서귀포시/모슬포'
  | '애월/한림/협재'
  | '중문'
  | '표선/성산'
  | '함덕/김녕/세화';

export type PlaceCategory = {
  id: string;
  label: string;
  icon: PlaceIconName;
};

export type Place = {
  id: string;
  name: string;
  address: string;
  /**
   * 서버 `places.region` 은 자유 문자열이라 앱의 지역 칩 6종에 못 맞추는 값이 있다.
   * 그때는 null 이고 '전체' 에서만 보인다. (`api/placeAdapter.ts` 참고)
   */
  region: PlaceRegion | null;
  category: string;
  /** 일정 추가 요청에 사용하는 DB 원본 분류 코드 */
  serverCategory?: string;
  environment?: '실내' | '야외';
  /** 좌표를 보내지 않으면 서버가 거리를 계산하지 않는다. 그때는 null. */
  distanceKm: number | null;
  latitude: number;
  longitude: number;
  /**
   * @deprecated 동반 정책은 5종(`petPolicy`)이다. 2026-08-18 확정.
   * 목데이터를 쓰는 장소 상세가 아직 참조해서 남겨 둔다.
   */
  petFriendly: boolean;
  /** 서버 `petPolicyType` 을 앱 표기로 옮긴 값. 배지가 이걸 그린다. */
  petPolicy?: PetPolicy;
  /** 사진이 없는 장소가 있다. RemoteImage 가 플레이스홀더를 그린다. */
  imageUrl: string | null;
  initiallyFavorite?: boolean;
};
