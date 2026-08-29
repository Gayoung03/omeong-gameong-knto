import type { PlaceCategory } from '../types/place';

/**
 * `serverCategories`가 서버 필터 값이고 `label`은 화면 표시값이다.
 * 어느 서버 코드가 어느 라벨로 보이는지는 `api/placeAdapter.ts`의
 * `CATEGORY_LABEL_BY_SERVER_CODE`가 정한다. **둘은 같이 고쳐야 한다.**
 *
 * '실내' · '야외' 는 분류가 아니라 `environment` 를 거른다. 한 줄에 같이 두는 것은
 * 사용자에게는 둘 다 "어떤 곳인지" 를 좁히는 같은 도구이기 때문이다.
 */
export const placeCategories: PlaceCategory[] = [
  {
    id: 'tour',
    label: '관광지',
    icon: 'partly-sunny-outline',
    serverCategories: ['attraction', 'beach', 'oreum', 'walking_trail'],
  },
  {
    id: 'cafe',
    label: '카페·식당',
    icon: 'cafe-outline',
    serverCategories: ['cafe', 'restaurant', 'restaurant_cafe'],
  },
  { id: 'stay', label: '숙소', icon: 'home-outline', serverCategories: ['accommodation'] },
  {
    id: 'hospital',
    label: '동물병원',
    icon: 'medkit-outline',
    serverCategories: ['veterinary_hospital', 'vet'],
  },
  // 미용·용품·호텔 등 66곳과 대여·체험 3곳. 칩이 없으면 '전체' 에서만 보인다.
  {
    id: 'service',
    label: '반려동물 서비스',
    icon: 'cut-outline',
    serverCategories: ['pet_service', 'rental_experience'],
  },
  { id: 'indoor', label: '실내', icon: 'business-outline' },
  { id: 'outdoor', label: '야외', icon: 'leaf-outline' },
];
