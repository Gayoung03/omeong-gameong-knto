/**
 * 장소 API 서버 응답 타입.
 *
 * `to_camel` 별칭이라 필드는 camelCase 지만 **enum 값은 snake_case** 다
 * (`outdoor_only`). 앱 타입으로 옮기는 일은 `api/placeAdapter.ts` 가 한다.
 */

export type PlacePetPolicyType =
  'indoor_allowed' | 'outdoor_only' | 'partial_allowed' | 'not_allowed' | 'unknown';

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

export type PlaceTagResponse = {
  code: string;
  name: string;
};

/**
 * 상세 조회에만 있는 동반 정책 전문.
 *
 * 목록은 `petPolicyType` 한 값만 내리고, 조건·출처·확인 시점은 여기서 받는다.
 * 정책 정보가 없는 장소는 `policyType` 이 `unknown` 이고 나머지가 대부분 `null` 이다.
 */
export type PlacePetPolicyResponse = {
  policyType: PlacePetPolicyType;
  allowedSpecies: string[] | null;
  allowedSizes: string[] | null;
  maxWeightKg: number | null;
  carrierRequired: boolean | null;
  leashRequired: boolean | null;
  vaccinationRequired: boolean | null;
  extraFeeAmount: number | null;
  notes: string | null;
  source: string | null;
  sourceUrl: string | null;
  /** ISO 8601 */
  verifiedAt: string | null;
  /** 0~100. 출처와 확인 시점에 따라 달라지는 신뢰도. */
  reliabilityScore: number | null;
};

/** 영업시간 한 줄. `dayOfWeek` 는 0(일요일) ~ 6(토요일). */
export type PlaceBusinessHourResponse = {
  dayOfWeek: number;
  /** 'HH:mm:ss' */
  opensAt: string | null;
  closesAt: string | null;
  breakStartAt: string | null;
  breakEndAt: string | null;
  isClosed: boolean;
  rawText: string | null;
};

export type PlaceDetailResponse = {
  id: string;
  name: string;
  category: string;
  region: string | null;
  address: string | null;
  roadAddress: string | null;
  latitude: number;
  longitude: number;
  phone: string | null;
  homepageUrl: string | null;
  primaryImageUrl: string | null;
  description: string | null;
  descriptionSource: string | null;
  environment: PlaceEnvironment | null;
  amenities: string[] | null;
  averageStayMinutes: number | null;
  reservationRequired: boolean;
  /** `created_by_user_id` 가 있으면 true. 사용자 id 자체는 내려오지 않는다. */
  isUserCreated: boolean;
  tags: PlaceTagResponse[];
  petPolicy: PlacePetPolicyResponse;
  businessHours: PlaceBusinessHourResponse[];
  reviewCount: number;
  savedCount: number;
  rating: number | null;
  isFavorite: boolean;
};
