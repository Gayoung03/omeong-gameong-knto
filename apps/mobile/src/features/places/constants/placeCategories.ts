import type { PlaceCategory } from '../types/place';

export const placeCategories: PlaceCategory[] = [
  { id: 'tour', label: '관광지', icon: 'partly-sunny-outline' },
  { id: 'cafe', label: '카페·식당', icon: 'cafe-outline' },
  { id: 'stay', label: '숙소', icon: 'home-outline' },
  { id: 'hospital', label: '동물병원', icon: 'medkit-outline' },
  { id: 'indoor', label: '실내', icon: 'business-outline' },
  { id: 'outdoor', label: '야외', icon: 'leaf-outline' },
];

// TODO: 장소 조회 API 연결 후 이 배열과 샘플 좌표를 검증된 위·경도 응답으로 교체합니다.
