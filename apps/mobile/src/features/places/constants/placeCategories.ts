import type { PlaceCategory } from '../types/place';

/**
 * `label` 이 필터 값이다 — 화면이 `place.category` 와 문자열을 맞춰 거른다.
 * 어느 서버 코드가 어느 라벨로 오는지는 `api/placeAdapter.ts` 의
 * `CATEGORY_LABEL_BY_SERVER_CODE` 가 정한다. **둘은 같이 고쳐야 한다.**
 *
 * 칩에 그리는 글자는 `chipLabel` 이 있으면 그쪽이다. 칩이 좁아 긴 라벨이 접히는데,
 * 필터 값인 `label` 은 줄일 수 없어서 표시용만 따로 둔다.
 *
 * '실내' · '야외' 는 분류가 아니라 `environment` 를 거른다. 한 줄에 같이 두는 것은
 * 사용자에게는 둘 다 "어떤 곳인지" 를 좁히는 같은 도구이기 때문이다.
 */
export const placeCategories: PlaceCategory[] = [
  { id: 'tour', label: '관광지', icon: 'partly-sunny-outline' },
  { id: 'cafe', label: '카페·식당', icon: 'cafe-outline' },
  { id: 'stay', label: '숙소', icon: 'home-outline' },
  { id: 'hospital', label: '동물병원', icon: 'medkit-outline' },
  // 미용·용품·호텔 등 66곳과 대여·체험 3곳. 칩이 없으면 '전체' 에서만 보인다.
  // 여덟 글자는 칩에서 세 줄로 접혀 잘린다. 칩에서만 '펫서비스' 로 줄이고,
  // 자리가 넉넉한 카드 태그와 지도 정보창에는 `label` 그대로 나간다.
  { id: 'service', label: '반려동물 서비스', chipLabel: '펫서비스', icon: 'cut-outline' },
  { id: 'indoor', label: '실내', icon: 'business-outline' },
  { id: 'outdoor', label: '야외', icon: 'leaf-outline' },
];
