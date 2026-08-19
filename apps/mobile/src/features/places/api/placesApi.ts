import { MOCK_TRIPS } from '@/src/features/trips/mocks/trips.mock';
import type { SchedulePlace } from '@/src/features/trips/types/trip';
import { getPlaceCategoryLabel } from '@/src/features/trips/utils/tripFormat';

import { mockPlaces } from '../mocks/place.mock';
import type { PlaceDetail } from '../types/placeDetail';
import type { Place } from '../types/place';

const RESPONSE_DELAY_MS = 250;

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
