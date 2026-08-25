import type { QuickMenuItem } from '../types/home';

import { categoryColors } from '@/src/theme';

export const quickMenuItems: QuickMenuItem[] = [
  {
    id: 'travel-guide',
    title: '여행 준비 가이드',
    subtitle: '제주 여행 정보',
    icon: 'book-outline',
    // 마이페이지 '나의 여행'의 같은 메뉴와 이름·아이콘·색을 맞춘다. (TravelSummarySection)
    iconColor: categoryColors.green.fg,
    iconBackgroundColor: categoryColors.green.bg,
    destination: 'travel-preparation',
  },
  {
    id: 'pet-friendly-place',
    title: '동반장소찾기',
    subtitle: '함께 갈 장소',
    icon: 'location-outline',
    iconColor: categoryColors.purple.fg,
    iconBackgroundColor: categoryColors.purple.bg,
    destination: 'place-explorer',
  },
  {
    id: 'travel-log',
    title: 'Log 만들기',
    subtitle: '여행 기록 남기기',
    icon: 'create-outline',
    iconColor: categoryColors.blue.fg,
    iconBackgroundColor: categoryColors.blue.bg,
    destination: 'travel-log-new',
  },
  {
    id: 'saved-places',
    title: '저장한 장소',
    subtitle: '찜한 곳 모아보기',
    icon: 'bookmark-outline',
    // 마이페이지 '나의 여행'의 같은 메뉴와 색을 맞춘다. (TravelSummarySection)
    iconColor: categoryColors.orange.fg,
    iconBackgroundColor: categoryColors.orange.bg,
    destination: 'saved-places',
  },
];

// TODO: 백엔드 크롤링 API가 준비되면 imageUrl과 title을 응답 데이터로 교체합니다.
