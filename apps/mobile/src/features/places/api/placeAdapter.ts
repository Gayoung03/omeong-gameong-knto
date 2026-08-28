import { toPetPolicy } from '@/src/types/place';

import type { PlaceDetailResponse, PlaceListItemResponse } from '../types/placeApi';
import type { Place, PlaceRegion } from '../types/place';
import type { PlaceDetail } from '../types/placeDetail';

/**
 * 서버 장소 → 앱 장소.
 *
 * 서버는 DB 생김새를 따르고(snake_case enum, 미터, 자유 문자열 지역)
 * 앱은 화면 사정을 따른다(camelCase union, km, 지역 칩 6종).
 * 둘 다 자기 쪽에선 맞는 선택이라 어느 한쪽을 굽히지 않고 여기서 번역만 한다.
 */

/**
 * 서버 `places.region` 은 `String(50)` 자유 문자열이고 앱의 지역 칩은 6종 union 이다.
 *
 * **운영 데이터는 관광권역 6개 이름을 통째로 보낸다** — `"애월/한림/협재"` 처럼.
 * 예전 표는 `"애월"` · `"한림"` 같은 짧은 이름만 받고 있어서 1268곳 중 1237곳이
 * `null` 이 됐다. 지역 칩을 눌러도 아무것도 안 나왔다. `"중문"` 만 우연히 권역
 * 이름과 짧은 이름이 같아 동작했다.
 *
 * 그래서 **권역 이름을 그대로 받는 것이 기본**이고, 짧은 이름은 씨앗 데이터가
 * 아직 쓰고 있어 함께 남긴다.
 *
 * **못 찾으면 null 로 둔다.** 아무 칩에나 끼워 넣으면 사용자가 "함덕"을 눌렀을 때
 * 엉뚱한 장소가 섞여 나온다. null 이면 '전체' 에서만 보인다.
 *
 * 예컨대 협재해수욕장은 서버 지역이 `"제주시"` 다(실제로는 한림). 짧은 이름을
 * 받아주면 **제주시 칩에 협재해수욕장이 뜬다.** 그래서 행정구역 이름은 받지 않는다.
 * 해당 장소는 4건이고, 값 자체를 고치는 것은 장소 데이터 회의 안건이다.
 */
const REGION_BY_SERVER_NAME: Record<string, PlaceRegion> = {
  // 운영 데이터가 쓰는 관광권역 이름.
  '제주시/제주국제공항': '제주시/제주국제공항',
  '서귀포시/모슬포': '서귀포시/모슬포',
  '애월/한림/협재': '애월/한림/협재',
  중문: '중문',
  '표선/성산': '표선/성산',
  '함덕/김녕/세화': '함덕/김녕/세화',

  // 씨앗 데이터(scripts/seed_dev.py)가 쓰는 짧은 이름.
  // 행정구역 이름(제주시·서귀포시)은 권역과 어긋나므로 넣지 않는다.
  제주국제공항: '제주시/제주국제공항',
  모슬포: '서귀포시/모슬포',
  애월: '애월/한림/협재',
  한림: '애월/한림/협재',
  한림읍: '애월/한림/협재',
  협재: '애월/한림/협재',
  표선: '표선/성산',
  성산: '표선/성산',
  함덕: '함덕/김녕/세화',
  김녕: '함덕/김녕/세화',
  세화: '함덕/김녕/세화',
};

/**
 * 서버 `places.category` 는 데이터 제공처가 준 코드 문자열이고,
 * 장소 탐색 화면의 분류 칩은 한글 라벨이다. 칩이 `place.category` 와
 * **문자열이 같은지**로 거르기 때문에 여기서 라벨로 옮겨야 필터가 동작한다.
 *
 * **서버가 실제로 보내는 값은 12종이다** (`app/rag/vocabulary.py` 참고).
 * 예전 표는 6줄뿐이었고 그중 `hospital` · `vet` 은 서버에 없는 값이었다 —
 * 실제 값은 `veterinary_hospital` 이라 동물병원 칩이 늘 0건이었다.
 * 나머지 누락으로 1268곳 중 414곳이 카드에 영문 코드를 그대로 노출했다.
 *
 * 해변·오름·산책로를 '관광지' 로 묶는 이유는, 칩을 12개로 늘리면 한 줄에 안 들어가고
 * 오름 12곳처럼 한 자리 수 분류가 칩을 차지하기 때문이다.
 *
 * 못 찾으면 서버 값을 그대로 둔다. 억지로 '기타' 로 바꾸면 화면에는 그럴듯하게
 * 보이지만 실제로 어떤 분류인지 알 수 없게 된다.
 *
 * `etc` 는 일부러 넣지 않는다. 278곳(21%)이 여기 묶여 있어 칩을 만들면 '기타' 가
 * 두 번째로 큰 분류가 된다. 분류를 쪼개는 것이 장소 데이터 회의 안건이고,
 * 정리되면 아래 표에 그대로 들어온다. 그때까지는 '전체' 에서만 보인다.
 *
 * **내 여행의 `getPlaceCategoryLabel` 과 라벨이 다르다** — 거기는 '카페/디저트',
 * 여기는 '카페·식당' 이다. `PlaceCategory` 이름 충돌과 함께 회의 안건이다.
 */
const CATEGORY_LABEL_BY_SERVER_CODE: Record<string, string> = {
  accommodation: '숙소',
  attraction: '관광지',
  beach: '관광지',
  oreum: '관광지',
  walking_trail: '관광지',
  cafe: '카페·식당',
  restaurant: '카페·식당',
  restaurant_cafe: '카페·식당',
  veterinary_hospital: '동물병원',
  pet_service: '반려동물 서비스',
  rental_experience: '반려동물 서비스',
};

function toRegion(serverRegion: string | null): PlaceRegion | null {
  if (!serverRegion) return null;
  return REGION_BY_SERVER_NAME[serverRegion] ?? null;
}

/** 목록·상세가 같은 라벨을 쓰도록 한곳에 둔다. */
export function toCategoryLabel(serverCategory: string): string {
  return CATEGORY_LABEL_BY_SERVER_CODE[serverCategory] ?? serverCategory;
}

/** 서버는 실내·야외·혼합 3종이고 화면은 두 글자 칩 두 개만 그린다. */
function toEnvironmentLabel(
  environment: PlaceListItemResponse['environment'],
): '실내' | '야외' | null {
  if (environment === 'indoor') return '실내';
  if (environment === 'outdoor') return '야외';
  return null;
}

export function toPlace(response: PlaceListItemResponse): Place {
  const petPolicy = toPetPolicy(response.petPolicyType);

  return {
    address: response.address ?? response.roadAddress ?? '',
    category: toCategoryLabel(response.category),
    // 서버는 미터, 화면은 km. 좌표를 안 보내면 서버가 null 을 주고 화면은 거리를 그리지 않는다.
    distanceKm: response.distanceMeters === null ? null : response.distanceMeters / 1000,
    environment: toEnvironmentLabel(response.environment) ?? undefined,
    id: response.id,
    imageUrl: response.primaryImageUrl,
    latitude: response.latitude,
    longitude: response.longitude,
    name: response.name,
    petPolicy,
    // 옛 boolean 필드. 배지가 5종을 그리므로 화면에서는 쓰지 않지만,
    // 목데이터를 보는 챗봇 지도 응답이 아직 참조해서 값을 맞춰 둔다.
    petFriendly: petPolicy !== 'notAllowed',
    region: toRegion(response.region),
  };
}

/**
 * 서버 장소 상세 → 화면 모델.
 *
 * 목록 어댑터와 두 가지가 다르다.
 * - **지역은 서버 원문 그대로** 쓴다. 상세에는 필터가 없어 칩에 맞출 이유가 없고,
 *   못 맞춘 값을 `null` 로 지우면 보여줄 수 있는 정보만 사라진다.
 * - 상세 응답에는 거리가 없다. 좌표 파라미터를 받지 않는 엔드포인트라 아예 안 온다.
 *
 * 전화번호 · 영업시간 · 태그 · 편의시설도 함께 내려오지만 아직 그리는 화면이 없어
 * 옮기지 않는다. 필요해지면 이 함수와 `PlaceDetail` 에 같이 추가한다.
 */
export function toPlaceDetail(response: PlaceDetailResponse): PlaceDetail {
  return {
    address: response.address ?? response.roadAddress ?? '',
    categoryLabel: toCategoryLabel(response.category),
    description: response.description,
    environment: toEnvironmentLabel(response.environment),
    id: response.id,
    imageUrl: response.primaryImageUrl,
    isReservable: response.reservationRequired,
    latitude: response.latitude,
    longitude: response.longitude,
    name: response.name,
    petPolicy: toPetPolicy(response.petPolicy.policyType),
    rating: response.rating,
    region: response.region,
    reviewCount: response.reviewCount,
    savedCount: response.savedCount,
  };
}
