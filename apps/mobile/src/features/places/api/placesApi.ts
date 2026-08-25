import { MOCK_TRIPS } from '@/src/features/trips/mocks/trips.mock';
import type { SchedulePlace } from '@/src/features/trips/types/trip';
import { getPlaceCategoryLabel } from '@/src/features/trips/utils/tripFormat';
import { apiClient } from '@/src/services/apiClient';

import { mockPlaces } from '../mocks/place.mock';
import type { PlaceDetail } from '../types/placeDetail';
import type { PlaceListResponse } from '../types/placeApi';
import type { Place } from '../types/place';

import { toPlace } from './placeAdapter';

const RESPONSE_DELAY_MS = 250;

/** 제주도 장소 수가 많지 않아 한 번에 받아 화면에서 거른다. */
const LIST_LIMIT = 100;

/**
 * 공식 장소 목록.
 *
 * 사용자가 등록한 "나만의 장소"는 여기 나오지 않는다. 서버가 경로를 나눠뒀다
 * (`GET /users/me/places`). 조건을 빠뜨리면 남이 등록한 장소가 이름·좌표째로
 * 섞이는 구조라, 섞일 수 없게 막아둔 것이다.
 */
export async function getPlaces(): Promise<Place[]> {
  const { data } = await apiClient.get<PlaceListResponse>('/places', {
    params: { limit: LIST_LIMIT },
  });

  return data.items.map(toPlace);
}

/** 장소명으로 검색한다. 서버가 좁혀 주므로 전체를 받아 거르지 않는다. */
export async function searchPlaces(query: string, limit = 20): Promise<Place[]> {
  const { data } = await apiClient.get<PlaceListResponse>('/places', {
    params: { q: query, limit },
  });

  return data.items.map(toPlace);
}

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

function fromPlace(place: Place): PlaceDetail {
  return {
    address: place.address,
    categoryLabel: place.category,
    description: null,
    distanceKm: place.distanceKm,
    environment: place.environment ?? null,
    id: place.id,
    imageUrl: place.imageUrl,
    isReservable: null,
    latitude: place.latitude,
    longitude: place.longitude,
    name: place.name,
    petFriendly: place.petFriendly,
    petPolicy: null,
    rating: null,
    region: place.region,
    reviewCount: null,
    savedCount: null,
    source: 'places',
  };
}

function fromSchedulePlace(place: SchedulePlace): PlaceDetail {
  return {
    address: place.address,
    categoryLabel: getPlaceCategoryLabel(place.category),
    description: place.description,
    distanceKm: null,
    environment: null,
    id: place.id,
    imageUrl: place.imageUrl,
    isReservable: place.isReservable,
    latitude: place.latitude,
    longitude: place.longitude,
    name: place.name,
    petFriendly: null,
    petPolicy: place.petPolicy,
    rating: place.rating,
    region: null,
    reviewCount: place.reviewCount,
    savedCount: place.savedCount,
    source: 'trips',
  };
}

/** 여행 목데이터 안에 흩어져 있는 장소를 한 줄로 편다. */
function collectTripPlaces(): SchedulePlace[] {
  return MOCK_TRIPS.flatMap((trip) =>
    trip.schedules.flatMap((schedule) => schedule.items.map((item) => item.place)),
  );
}

/**
 * 장소 상세 조회.
 *
 * 장소 탐색과 내 여행의 id 체계가 서로 달라(`hamdeok-beach` vs `place-hyeopjae`)
 * 두 목데이터를 차례로 찾는다.
 *
 * TODO: 장소 API(GET /places/{placeId})가 준비되면 이 함수만 실제 호출로 바꾼다.
 *       화면과 훅은 `PlaceDetail` 만 보므로 그대로 둔다.
 */
export async function getPlaceDetail(placeId: string): Promise<PlaceDetail | null> {
  await wait(RESPONSE_DELAY_MS);

  const place = mockPlaces.find((item) => item.id === placeId);
  if (place) {
    return fromPlace(place);
  }

  const tripPlace = collectTripPlaces().find((item) => item.id === placeId);
  if (tripPlace) {
    return fromSchedulePlace(tripPlace);
  }

  return null;
}
