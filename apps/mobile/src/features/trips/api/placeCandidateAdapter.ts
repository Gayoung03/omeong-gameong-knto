import { toPetPolicy } from '@/src/types/place';
import type { PlaceListItemResponse } from '@/src/features/places/types/placeApi';

import type { PlaceCandidate, PlaceCategory } from '../types/trip';

/**
 * 서버 장소 → 일정 추가 화면의 장소 후보.
 *
 * 장소 탐색의 `placeAdapter.toPlace` 와 목적지가 다르다. 그쪽은 한글 라벨 문자열을
 * 만들고(칩이 문자열 비교로 거른다), 여기는 **분류 union** 이 필요하다
 * (`PLACE_FILTER_CATEGORIES` 가 union 값으로 필터를 정의한다).
 * 같은 서버 값을 두 방향으로 옮기는 것이라 어댑터도 둘이다.
 *
 * `PlaceCategory` 라는 이름이 두 기능에서 서로 다른 뜻으로 쓰이는 것이
 * 이 혼란의 뿌리다 — 회의 안건으로 올라가 있다.
 */

const CATEGORY_BY_SERVER_CODE: Record<string, PlaceCategory> = {
  accommodation: 'accommodation',
  attraction: 'attraction',
  beach: 'attraction',
  cafe: 'cafe',
  oreum: 'attraction',
  rental_experience: 'attraction',
  restaurant: 'restaurant',
  restaurant_cafe: 'restaurant',
  walking_trail: 'attraction',
};

/**
 * 모르는 분류는 `etc` 다.
 *
 * `etc` 는 어떤 필터 칩에도 안 들어가서 '맛집·관광·숙소' 를 누르면 사라지고
 * 필터를 끄면 다시 보인다. 억지로 관광지에 넣으면 관광 필터가 거짓말을 한다.
 */
function toCategory(serverCategory: string): PlaceCategory {
  return CATEGORY_BY_SERVER_CODE[serverCategory] ?? 'etc';
}

export function toPlaceCandidate(response: PlaceListItemResponse): PlaceCandidate {
  return {
    address: response.address ?? response.roadAddress ?? '',
    category: toCategory(response.category),
    // 목록 응답에는 소개글이 없다(상세 조회에만 있다). 카드가 설명 줄을 그리지 않는다.
    description: '',
    id: response.id,
    imageUrl: response.primaryImageUrl,
    isReservable: response.reservationRequired,
    latitude: response.latitude,
    longitude: response.longitude,
    name: response.name,
    petPolicy: toPetPolicy(response.petPolicyType),
    rating: response.rating,
    // 서버 원문. 칩 6종으로 옮기지 않는다 — 여기서는 카드에 한 줄로 보여주기만 한다.
    regionLabel: response.region ?? '',
    reviewCount: response.reviewCount,
    savedCount: response.savedCount,
  };
}
