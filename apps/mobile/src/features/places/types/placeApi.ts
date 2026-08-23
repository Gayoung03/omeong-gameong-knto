/**
 * 장소 API 서버 응답 타입.
 *
 * `to_camel` 별칭이라 필드는 camelCase 지만 **enum 값은 snake_case** 다
 * (`outdoor_only`). 앱 타입으로 옮기는 일은 `api/placeAdapter.ts` 가 한다.
 */

export type PlacePetPolicyType =
  | 'indoor_allowed'
  | 'outdoor_only'
  | 'partial_allowed'
  | 'not_allowed'
  | 'unknown';

export type PlaceEnvironment = 'indoor' | 'outdoor' | 'mixed';

export type PlaceListItemResponse = {
  id: string;
  name: string;
  category: string;
  region: string | null;
  address: string | null;
  roadAddress: string | null;
  latitude: number;
  longitude: number;
  primaryImageUrl: string | null;
  environment: PlaceEnvironment | null;
  petPolicyType: PlacePetPolicyType;
  tags: string[];
  reservationRequired: boolean;
  /** 좌표를 보내지 않으면 null. */
  distanceMeters: number | null;
  reviewCount: number;
  savedCount: number;
  rating: number | null;
  isFavorite: boolean;
};

export type PlaceListResponse = {
  items: PlaceListItemResponse[];
  total: number;
  limit: number;
  offset: number;
};

export type FavoritePlaceResponse = PlaceListItemResponse & {
  /** ISO 8601. 즐겨찾기에 넣은 시각. */
  favoritedAt: string;
};

export type FavoritePlaceListResponse = {
  items: FavoritePlaceResponse[];
  total: number;
  limit: number;
  offset: number;
};
