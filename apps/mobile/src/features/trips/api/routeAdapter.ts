/**
 * 서버 여행(route) 응답 → 앱 여행(trip) 타입 변환.
 *
 * 서버와 앱의 타입이 다르게 자란 곳을 **여기 한 곳에서만** 흡수한다.
 * 화면·훅은 `../types/trip.ts` 만 보고, 서버 생김새를 몰라야 한다.
 * (`features/places/api/placesApi.ts` 의 장소 상세 어댑터와 같은 방식이다.)
 *
 * 서버에 아직 없는 값은 화면이 그리지 않는 빈 값(null·0·'')으로 채운다.
 * 서버가 값을 내려주기 시작하면 이 파일만 고치면 된다.
 */

import type {
  PlaceSummaryResponse,
  RouteDayResponse,
  RouteDetailResponse,
  RouteItemResponse,
  RouteListItemResponse,
  RoutePetResponse,
  ServerScheduleItemType,
  ServerTransportType,
  ServerTripPace,
} from '../types/routeApi';
import type {
  PlaceCategory,
  Schedule,
  ScheduleItem,
  SchedulePlace,
  Trip,
  TripDistanceSummary,
  TripListItem,
  TripPet,
  TripTransport,
} from '../types/trip';

/**
 * 여행 표지 이모지. 서버 응답에 없다.
 * "화면에 보일 것은 앱이 만든다"가 팀 원칙이라 앱에서 고정값으로 붙인다.
 */
const TRIP_COVER_EMOJI = '🐶';

/**
 * 서버 이동수단(7종) → 앱 이동수단(4종).
 *
 * `taxi`·`ferry`·`airplane` 은 앱 union 에 없어 가장 가까운 값으로 접는다.
 * 정보가 줄어드는 변환이라 **앱 union 을 넓힐지 회의 안건**이다.
 */
const TRANSPORT_MAP: Record<ServerTransportType, TripTransport> = {
  rental_car: 'rentalCar',
  own_car: 'ownCar',
  public_transport: 'publicTransport',
  walk: 'walk',
  taxi: 'publicTransport',
  ferry: 'publicTransport',
  airplane: 'publicTransport',
};

/** 서버 일정 분류 → 앱 장소 분류. 직접 입력(`custom`)은 앱에 대응 값이 없어 `etc` 다 */
const CATEGORY_MAP: Record<ServerScheduleItemType, PlaceCategory> = {
  attraction: 'attraction',
  restaurant: 'restaurant',
  cafe: 'cafe',
  accommodation: 'accommodation',
  custom: 'etc',
};

/**
 * 여행 속도 → 화면의 '여행 성향' 한 줄.
 * 서버 `explanation` 은 문단이라 이 한 줄 자리에 맞지 않는다.
 */
const PACE_LABEL: Record<ServerTripPace, string> = {
  relaxed: '여유로운 힐링 여행',
  normal: '알차게 둘러보는 여행',
  packed: '부지런히 많이 보는 여행',
};

/** 이동 요약은 TMAP 연동 전까지 서버에 없다. 화면은 0 을 그대로 그린다 */
const EMPTY_DISTANCE_SUMMARY: TripDistanceSummary = {
  totalDistanceKm: 0,
  carMinutes: 0,
  walkMinutes: 0,
};

/**
 * ISO 8601 → 'YYYY-MM-DD'.
 *
 * 서버가 `+09:00` 으로 내려주므로 **앞 10글자가 곧 한국 날짜**다.
 * UTC(`Z`)로 오면 이른 아침 일정의 날짜가 하루 밀린다 —
 * 그래서 `apps/api/app/db/session.py` 가 DB 세션 시간대를 Asia/Seoul 로 고정해 둔 것이다.
 */
function toKstDate(iso: string): string {
  return iso.slice(0, 10);
}

/** ISO 8601 → 'HH:mm'. 시각을 안 정한 일정이면 null */
function toKstTime(iso: string | null): string | null {
  return iso ? iso.slice(11, 16) : null;
}

function toTripPet(pet: RoutePetResponse): TripPet {
  return {
    id: pet.id,
    name: pet.name,
    // 서버에 크기가 없으면 화면이 '중형'으로 보이게 둔다. 배지가 비는 것보다 낫다.
    sizeType: pet.size ?? 'medium',
    // 서버는 반려동물을 개체로 관리해 마리 수 개념이 없다. 한 줄에 한 마리.
    count: 1,
  };
}

function toSchedulePlace(item: RouteItemResponse, place: PlaceSummaryResponse): SchedulePlace {
  return {
    id: place.id,
    // 직접 입력한 이름이 있으면 그쪽이 사용자가 실제로 적은 이름이다.
    name: item.customPlaceName ?? place.name,
    // place.category 는 자유 문자열이라 앱 union 을 보장하지 못한다.
    // 값이 정해진 item_type 을 쓴다.
    category: CATEGORY_MAP[item.itemType] ?? 'etc',
    description: place.description ?? '',
    // 동반 정책은 place_pet_policies 연동 전까지 없다. 회색 '정보 없음' 배지가 뜬다.
    petPolicy: 'unknown',
    address: place.address ?? '',
    // 리뷰 집계가 아직 없다.
    rating: null,
    reviewCount: 0,
    savedCount: 0,
    imageUrl: place.primaryImageUrl,
    latitude: place.latitude,
    longitude: place.longitude,
    isReservable: place.reservationRequired,
  };
}

function toScheduleItem(item: RouteItemResponse, index: number): ScheduleItem {
  return {
    id: item.id,
    // 서버 sortOrder 는 0 부터, 화면 순번 배지는 1 부터다.
    // useScheduleEdit·useAddSchedule 도 index + 1 로 다시 매긴다 — 같은 규칙을 쓴다.
    order: index + 1,
    place: toSchedulePlace(item, item.place as PlaceSummaryResponse),
    // 즐겨찾기 여부는 AsyncStorage(features/saved) 가 갖고 있고 서버 응답에 없다.
    isSaved: false,
    startTime: toKstTime(item.startsAt),
    memo: item.note ?? '',
    // 일정 사이 이동 정보는 TMAP 연동 전까지 없다.
    moveToNext: null,
  };
}

function toSchedule(day: RouteDayResponse): Schedule {
  /**
   * 공식 장소가 연결되지 않은 일정은 좌표가 없어 지도 탭이 깨진다.
   * 지금은 걸러내되 조용히 삼키지 않는다 — 일정 편집 API 를 만들 때 제대로 다뤄야 할 지점이다.
   */
  const items = day.items.filter((item) => {
    if (item.place) return true;
    if (__DEV__) {
      console.warn(
        `[trips] 좌표가 없어 일정을 건너뜁니다: ${item.customPlaceName ?? item.id} (day ${day.dayNumber})`,
      );
    }
    return false;
  });

  return {
    id: day.id,
    dayNumber: day.dayNumber,
    // 서버가 date 타입이라 이미 'YYYY-MM-DD' 다.
    date: day.routeDate,
    // 날씨는 기상청 연동 전까지 없다. null 이면 화면이 날씨 칸을 그리지 않는다.
    weather: null,
    items: items.map(toScheduleItem),
  };
}

/**
 * 숙소 요약. 서버의 `stays` 는 아직 없지만
 * 일정 안의 숙소 항목에서 이름을 뽑아낼 수 있다. 중복은 없앤다.
 */
function toAccommodationSummary(days: RouteDayResponse[]): string {
  const names = days
    .flatMap((day) => day.items)
    .filter((item) => item.itemType === 'accommodation')
    .map((item) => item.customPlaceName ?? item.place?.name)
    .filter((name): name is string => Boolean(name));

  return [...new Set(names)].join(', ');
}

/** 목록 한 줄 변환 */
export function toTripListItem(route: RouteListItemResponse): TripListItem {
  return {
    id: route.id,
    title: route.title,
    startDate: toKstDate(route.startAt),
    endDate: toKstDate(route.endAt),
    nights: route.nights,
    days: route.days,
    coverEmoji: TRIP_COVER_EMOJI,
  };
}

/** 상세 변환 */
export function toTrip(route: RouteDetailResponse): Trip {
  return {
    ...toTripListItem(route),
    transport: TRANSPORT_MAP[route.transport] ?? 'rentalCar',
    pets: route.pets.map(toTripPet),
    accommodationSummary: toAccommodationSummary(route.routeDays),
    travelStyle: PACE_LABEL[route.pace] ?? '',
    styleKeywords: route.styleKeywords ?? [],
    memo: route.memo ?? '',
    distanceSummary: EMPTY_DISTANCE_SUMMARY,
    schedules: route.routeDays.map(toSchedule),
  };
}
