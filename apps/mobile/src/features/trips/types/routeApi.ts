/**
 * 서버(FastAPI) 여행 API 의 응답 타입.
 *
 * 정본은 `docs/api/routes.md` 와 `apps/api/app/schemas/route.py` 다.
 * 서버 스키마가 `alias_generator=to_camel` 을 쓰므로 JSON 은 camelCase 로 온다.
 *
 * 화면이 쓰는 타입은 `./trip.ts` 이고 생김새가 다르다.
 * 둘 사이 변환은 `../api/routeAdapter.ts` 한 곳에서만 한다 — 화면은 이 파일을 몰라야 한다.
 *
 * `Server~` 접두사가 붙은 값은 DB enum 이라 **snake_case** 다 (`rental_car`).
 * 앱 쪽 union 은 camelCase(`rentalCar`) 이므로 그대로 쓰면 안 된다.
 */

/** 여행 상태 */
export type ServerRouteStatus =
  'generating' | 'generated' | 'saved' | 'ongoing' | 'completed' | 'failed';

/** 여행이 만들어진 방식 */
export type ServerRouteCreationType = 'recommended' | 'manual';

/** 여행 속도 */
export type ServerTripPace = 'relaxed' | 'normal' | 'packed';

/** 여행 전체 이동 수단. 앱의 `TripTransport` 보다 종류가 많다 */
export type ServerTransportType =
  'rental_car' | 'own_car' | 'taxi' | 'public_transport' | 'walk' | 'ferry' | 'airplane';

/** 반려동물 종 */
export type ServerPetSpecies = 'dog' | 'cat' | 'rabbit' | 'bird' | 'other';

/** 반려동물 크기 */
export type ServerPetSize = 'small' | 'medium' | 'large';

/** 일정 항목의 분류. 앱의 `PlaceCategory` 와 대응한다 */
export type ServerScheduleItemType =
  'attraction' | 'restaurant' | 'cafe' | 'accommodation' | 'custom';

/** GET /routes 의 한 줄 */
export type RouteListItemResponse = {
  id: string;
  title: string;
  status: ServerRouteStatus;
  creationType: ServerRouteCreationType;
  version: number;
  /** ISO 8601. DB 세션 시간대가 Asia/Seoul 이라 `+09:00` 으로 온다 */
  startAt: string;
  endAt: string;
  pace: ServerTripPace;
  transport: ServerTransportType;
  coverImageUrl: string | null;
  styleKeywords: string[] | null;
  petSafetyScore: number | null;
  isPublic: boolean;
  /** 서버가 start/end 로 계산해 내려준다 (DB 에 없는 값) */
  days: number;
  nights: number;
};

/**
 * 목록 응답. 배열을 그대로 내리지 않고 감싼다 (`docs/api/README.md` 5장).
 * `total` 은 `limit` 에 잘리지 않은 전체 개수다.
 */
export type RouteListResponse = {
  items: RouteListItemResponse[];
  total: number;
  limit: number;
  offset: number;
};

/** 일정에 담긴 장소 요약 */
export type PlaceSummaryResponse = {
  id: string;
  name: string;
  category: string;
  address: string | null;
  description: string | null;
  primaryImageUrl: string | null;
  latitude: number;
  longitude: number;
  reservationRequired: boolean;
};

/** 하루 안의 방문 한 건 */
export type RouteItemResponse = {
  id: string;
  /** 0 부터 시작한다. 앱의 `order` 는 1 부터라 어댑터에서 다시 매긴다 */
  sortOrder: number;
  itemType: ServerScheduleItemType;
  /** ISO 8601 `+09:00`. 시각을 안 정했으면 null */
  startsAt: string | null;
  endsAt: string | null;
  stayMinutes: number | null;
  note: string | null;
  isSelected: boolean;
  recommendationScore: number | null;
  recommendationReason: string | null;
  /** 공식 장소가 아닌 직접 입력 일정의 이름. 이때 `place` 는 null 이다 */
  customPlaceName: string | null;
  place: PlaceSummaryResponse | null;
};

/** 여행의 하루 */
export type RouteDayResponse = {
  id: string;
  dayNumber: number;
  /** YYYY-MM-DD */
  routeDate: string;
  title: string | null;
  items: RouteItemResponse[];
};

/** 이 여행에 함께 가는 반려동물 */
export type RoutePetResponse = {
  id: string;
  name: string;
  species: ServerPetSpecies;
  speciesDetail: string | null;
  size: ServerPetSize | null;
};

/**
 * GET /routes/{routeId}.
 *
 * 명세에 있지만 아직 서버가 안 내려주는 것 —
 * `weather` · `moveToNext` · `distanceSummary` · `stays` · `logCount` ·
 * place 의 `rating`·`reviewCount`·`petPolicyType`.
 * 데이터 소스(기상청·TMAP·리뷰 집계)가 아직 없어서다.
 */
export type RouteDetailResponse = RouteListItemResponse & {
  explanation: string | null;
  totalScore: number | null;
  memo: string | null;
  shareToken: string | null;
  pets: RoutePetResponse[];
  routeDays: RouteDayResponse[];
};
