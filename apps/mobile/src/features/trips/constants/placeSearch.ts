import type Ionicons from '@expo/vector-icons/Ionicons';

import type { PlaceCategory, PlaceFilter, PlaceSourceTab } from '../types/trip';

/** 지도 위 카테고리 필터 칩 */
export const PLACE_FILTER_OPTIONS: {
  value: PlaceFilter;
  label: string;
  iconName: keyof typeof Ionicons.glyphMap;
}[] = [
  { value: 'restaurant', label: '맛집', iconName: 'restaurant' },
  { value: 'attraction', label: '관광', iconName: 'flag' },
  { value: 'accommodation', label: '숙소', iconName: 'business' },
];

/**
 * 필터 하나가 포함하는 장소 분류.
 * '맛집'은 음식점과 카페를 함께 보여준다.
 */
export const PLACE_FILTER_CATEGORIES: Record<PlaceFilter, PlaceCategory[]> = {
  restaurant: ['restaurant', 'cafe'],
  attraction: ['attraction'],
  accommodation: ['accommodation'],
};

/** 바텀시트 상단의 출처 탭 */
export const PLACE_SOURCE_TAB_OPTIONS: { value: PlaceSourceTab; label: string }[] = [
  { value: 'dayRecommend', label: '추천' },
  { value: 'recentSaved', label: '최근 저장' },
  { value: 'nearStay', label: '내 숙소' },
  { value: 'myPlace', label: '나만의 장소' },
];

/** 탭별로 목록이 비었을 때 보여줄 안내 문구 */
export const PLACE_SOURCE_EMPTY_MESSAGES: Record<PlaceSourceTab, string> = {
  dayRecommend: '이 날짜 루트 근처에서 추천할 장소를 찾지 못했어요',
  recentSaved: '최근 저장한 장소가 없어요',
  nearStay: '숙소를 먼저 일정에 담으면 근처 장소를 추천해드려요',
  myPlace: '직접 등록한 장소가 없어요',
};

/** 지도에 후보를 최대 몇 개까지 표시할지 */
export const MAX_MAP_CANDIDATES = 20;
