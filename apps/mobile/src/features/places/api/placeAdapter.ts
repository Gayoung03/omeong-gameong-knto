import { toPetPolicy } from '@/src/types/place';

import type { PlaceListItemResponse } from '../types/placeApi';
import type { Place, PlaceRegion } from '../types/place';

/**
 * 서버 장소 → 앱 장소.
 *
 * 서버는 DB 생김새를 따르고(snake_case enum, 미터, 자유 문자열 지역)
 * 앱은 화면 사정을 따른다(camelCase union, km, 지역 칩 6종).
 * 둘 다 자기 쪽에선 맞는 선택이라 어느 한쪽을 굽히지 않고 여기서 번역만 한다.
 */

/**
 * 서버 `places.region` 은 `String(50)` 자유 문자열이고 앱의 지역 칩은 6종 union 이다.
 * 씨앗 데이터가 "제주시" · "서귀포시" 처럼 행정구역 이름을 쓰고 있어 칩 이름과 다르다.
 *
 * **못 찾으면 null 로 둔다.** 아무 칩에나 끼워 넣으면 사용자가 "함덕"을 눌렀을 때
 * 엉뚱한 장소가 섞여 나온다. null 이면 '전체' 에서만 보인다.
 *
 * 지역 값 통일은 회의 안건이다 — 서버 데이터에 손대야 해서 되돌리기가 비싸다.
 */
const REGION_BY_SERVER_NAME: Record<string, PlaceRegion> = {
  '제주시': '제주시/제주국제공항',
  '제주국제공항': '제주시/제주국제공항',
  '서귀포시': '서귀포시/모슬포',
  '모슬포': '서귀포시/모슬포',
  '애월': '애월/한림/협재',
  '한림': '애월/한림/협재',
  '한림읍': '애월/한림/협재',
  '협재': '애월/한림/협재',
  '중문': '중문',
  '표선': '표선/성산',
  '성산': '표선/성산',
  '함덕': '함덕/김녕/세화',
  '김녕': '함덕/김녕/세화',
  '세화': '함덕/김녕/세화',
};

/**
 * 서버 `places.category` 는 데이터 제공처가 준 코드 문자열이고,
 * 장소 탐색 화면의 분류 칩은 한글 라벨 6종이다. 칩이 `place.category` 와
 * **문자열이 같은지**로 거르기 때문에 여기서 라벨로 옮겨야 필터가 동작한다.
 *
 * 못 찾으면 서버 값을 그대로 둔다. 억지로 '기타' 로 바꾸면 화면에는 그럴듯하게
 * 보이지만 실제로 어떤 분류인지 알 수 없게 된다.
 *
 * **내 여행의 `getPlaceCategoryLabel` 과 라벨이 다르다** — 거기는 '카페/디저트',
 * 여기는 '카페·식당' 이다. `PlaceCategory` 이름 충돌과 함께 회의 안건이다.
 */
const CATEGORY_LABEL_BY_SERVER_CODE: Record<string, string> = {
  accommodation: '숙소',
  attraction: '관광지',
  cafe: '카페·식당',
  hospital: '동물병원',
  restaurant: '카페·식당',
  vet: '동물병원',
};

function toRegion(serverRegion: string | null): PlaceRegion | null {
  if (!serverRegion) return null;
  return REGION_BY_SERVER_NAME[serverRegion] ?? null;
}

export function toPlace(response: PlaceListItemResponse): Place {
  const petPolicy = toPetPolicy(response.petPolicyType);

  return {
    address: response.address ?? response.roadAddress ?? '',
    category: CATEGORY_LABEL_BY_SERVER_CODE[response.category] ?? response.category,
    // 서버는 미터, 화면은 km. 좌표를 안 보내면 서버가 null 을 주고 화면은 거리를 그리지 않는다.
    distanceKm: response.distanceMeters === null ? null : response.distanceMeters / 1000,
    environment:
      response.environment === 'indoor'
        ? '실내'
        : response.environment === 'outdoor'
          ? '야외'
          : undefined,
    id: response.id,
    imageUrl: response.primaryImageUrl,
    latitude: response.latitude,
    longitude: response.longitude,
    name: response.name,
    petPolicy,
    // 옛 boolean 필드. 배지가 5종을 그리므로 화면에서는 쓰지 않지만,
    // 목데이터를 쓰는 장소 상세가 아직 참조해서 값을 맞춰 둔다.
    petFriendly: petPolicy !== 'notAllowed',
    region: toRegion(response.region),
  };
}
