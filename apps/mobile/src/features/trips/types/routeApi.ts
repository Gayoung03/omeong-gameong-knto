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

import type { ServerPetPolicy } from '@/src/types/place';

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

/**
 * 슬롯 상태 **[재설계 2026-09-07]**.
 * `unfilled` 면 `place`·시각이 null 이고 `candidates` 에 확인 필요 후보가 붙는다.
 * `needs_verification` 이면 장소는 있지만 동반 여부가 미확인이라 "확인 필요" 라벨과
 * `place.phone` 을 같이 보여준다.
 */
export type ServerRouteItemSlotStatus = 'filled' | 'needs_verification' | 'unfilled';

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
  /** 이 여행에 속한 여행기록 개수. 계산값이다 */
  logCount: number;
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
  /** 리뷰 집계. 2026-08-23 부터 서버가 내려준다 */
  rating: number | null;
  reviewCount: number;
  petPolicyType: ServerPetPolicy;
  /** 확인 필요 슬롯의 확인 전화용. 2026-09-09 부터 내려온다 */
  phone: string | null;
};

/**
 * 슬롯별 대안 후보 (`route_item_candidates`, 최대 3개).
 * `edit-suggestions` 의 항목 모양에 `requiresVerification`·`phone` 이 붙었다.
 * 같은 날짜의 항목이 편집되면 그 날짜의 후보는 모두 지워져 빈 배열이 된다.
 */
export type RouteItemCandidateResponse = {
  placeId: string;
  name: string;
  category: string;
  address: string | null;
  primaryImageUrl: string | null;
  phone: string | null;
  recommendationScore: number | null;
  recommendationReason: string | null;
  /** 동반 여부가 미확인인 후보. 담으면 슬롯이 `needs_verification` 이 된다 */
  requiresVerification: boolean;
};

/** `slotStatus` 집계(계산값). 출발지·숙소 앵커는 빼고 방문 슬롯만 센다 */
export type RouteSlotSummaryResponse = {
  total: number;
  filled: number;
  needsVerification: number;
  unfilled: number;
};

/** 동선·숙소 근처 동물병원 안전망(계산값, 저장 안 함). `id` 는 `places.id` */
export type NearbyAnimalHospitalResponse = {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
  latitude: number;
  longitude: number;
  distanceMeters: number;
  /** 이름의 "24시" 로만 판정한다 (영업시간 데이터 없음) */
  is24Hours: boolean;
};

/** 하루 안의 방문 한 건 */
export type RouteItemResponse = {
  id: string;
  /** 0 부터 시작한다. 앱의 `order` 는 1 부터라 어댑터에서 다시 매긴다 */
  sortOrder: number;
  itemType: ServerScheduleItemType;
  slotStatus: ServerRouteItemSlotStatus;
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
  customAddress: string | null;
  latitude: number | null;
  longitude: number | null;
  place: PlaceSummaryResponse | null;
  candidates: RouteItemCandidateResponse[];
  moveToNext: {
    transport: ServerTransportType;
    distanceMeters: number;
    durationMinutes: number;
    /** TMAP 캐시가 없어 추정식으로 채운 구간 */
    isEstimated: boolean;
  } | null;
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
 * 명세에 있지만 아직 서버가 안 내려주는 것 — `weather`(기상청).
 *
 * `logCount` 와 place 의 `rating`·`reviewCount`·`petPolicyType` 은
 * 2026-08-23 에 채워졌다.
 */
export type RouteDetailResponse = RouteListItemResponse & {
  explanation: string | null;
  totalScore: number | null;
  memo: string | null;
  /** 구버전 서버와의 순차 배포 중에는 필드가 없을 수 있다. */
  departureLocation?: string | null;
  stays?: RouteStayCreateRequest[];
  shareToken: string | null;
  pets: RoutePetResponse[];
  distanceSummary: {
    totalDistanceMeters: number;
    totalDurationMinutes: number;
  };
  /** 상세 조회 시 TourAPI에서 실시간으로 받은 주변 관광정보. DB에는 저장하지 않는다. */
  tourApiPlaces: {
    contentId: string;
    title: string;
    address: string | null;
    latitude: number;
    longitude: number;
    imageUrl: string | null;
  }[];
  routeDays: RouteDayResponse[];
  slotSummary: RouteSlotSummaryResponse;
  nearbyAnimalHospitals: NearbyAnimalHospitalResponse[];
};

/**
 * POST /route-days/{routeDayId}/items 요청.
 *
 * `sortOrder` 는 0 부터다. 이미 있는 값이면 뒤 항목들이 밀린다.
 * `placeId` 가 없으면 `customPlaceName` 이 필수다.
 */
export type RouteItemCreateRequest = {
  itemType: ServerScheduleItemType;
  sortOrder: number;
  placeId?: string;
  customPlaceName?: string;
  startsAt?: string;
  endsAt?: string;
  stayMinutes?: number;
  note?: string;
};

/**
 * PATCH /routes/{routeId} 요청. **보낸 필드만** 바뀐다.
 *
 * `status` 는 아무 값이나 못 넣는다. 서버가 허용하는 전이는
 * `generated → saved → ongoing → completed` 한 방향뿐이고
 * 어긋나면 422 다. 같은 상태를 다시 보내는 것은 통과한다.
 *
 * `isPublic` 을 false 로 보내는 것이 곧 **공유 해제**다(별도 엔드포인트가 없다).
 */
export type RouteUpdateRequest = {
  title?: string;
  status?: ServerRouteStatus;
  styleKeywords?: string[] | null;
  memo?: string | null;
  coverImageUrl?: string | null;
  isPublic?: boolean;
};

/** POST /routes — 추천 없이 여행의 기본 정보와 날짜를 직접 만든다. */
export type ManualRouteCreateRequest = {
  title: string;
  startAt: string;
  endAt: string;
  pace: ServerTripPace;
  transport: ServerTransportType;
  petIds: string[];
  departureLocation?: string;
  stays: RouteStayCreateRequest[];
};

/**
 * PATCH /route-items/{routeItemId} 요청. **보낸 필드만** 바뀐다.
 *
 * 순서(`sortOrder`)는 여기서 못 바꾼다 — UNIQUE 제약 때문에
 * 그 날짜 전체를 순서 API 로 한 번에 보내야 한다.
 * 날짜 이동도 없다 — 지웠다가 새 날짜에 다시 만든다(`api/scheduleSync.ts`).
 */
export type RouteItemUpdateRequest = {
  startsAt?: string | null;
  endsAt?: string | null;
  stayMinutes?: number | null;
  note?: string | null;
  isSelected?: boolean;
};

export type RouteStayCreateRequest = {
  placeId?: string;
  name: string;
  address?: string;
  checkInAt?: string;
  checkOutAt?: string;
};

export type RouteRequestCreateRequest = {
  title?: string;
  startAt: string;
  endAt: string;
  departureLocation?: string;
  departurePlaceId?: string;
  pace: ServerTripPace;
  transport: ServerTransportType;
  companionCount: number;
  preferredTags: string[];
  priorityPreset: string;
  userCriteria: string[];
  requestText?: string;
  petIds: string[];
  stays: RouteStayCreateRequest[];
};

export type RouteRequestAcceptedResponse = {
  routeId: string;
  routeRequestId: string;
  status: ServerRouteStatus;
  version: number;
};

export type RouteGenerationStatusResponse = {
  routeId: string;
  status: ServerRouteStatus;
  version: number;
  failureReason: string | null;
  /** 생성 완료 시에만 채운다. 그 외 null */
  slotSummary: RouteSlotSummaryResponse | null;
};

export type RouteReplacementSuggestionResponse = {
  placeId: string;
  name: string;
  category: string;
  address: string | null;
  primaryImageUrl: string | null;
  recommendationScore: number;
  recommendationReason: string;
};

export type RouteEditSuggestionResponse = {
  targetItemId: string;
  interpretation: string;
  suggestions: RouteReplacementSuggestionResponse[];
};
