import type { QuickMenuItem } from '../types/home';

import { categoryColors } from '@/src/theme';

export const quickMenuItems: QuickMenuItem[] = [
  {
    id: 'travel-guide',
    title: '여행가이드',
    subtitle: '제주 여행 정보',
    icon: 'book-outline',
    iconColor: categoryColors.green.fg,
    iconBackgroundColor: categoryColors.green.bg,
    destination: 'coming-soon',
  },
  {
    id: 'pet-friendly-place',
    title: '동반장소찾기',
    subtitle: '함께 갈 장소',
    icon: 'location-outline',
    iconColor: categoryColors.orange.fg,
    iconBackgroundColor: categoryColors.orange.bg,
    destination: 'place-explorer',
  },
  {
    id: 'pet-character',
    title: '내 캐릭터 만들기',
    subtitle: '우리 아이 캐릭터',
    icon: 'paw-outline',
    iconColor: categoryColors.yellow.fg,
    iconBackgroundColor: categoryColors.yellow.bg,
    destination: 'coming-soon',
  },
  {
    id: 'travel-log',
    title: 'Log 만들기',
    subtitle: '여행 기록 남기기',
    icon: 'create-outline',
    iconColor: categoryColors.blue.fg,
    iconBackgroundColor: categoryColors.blue.bg,
    destination: 'coming-soon',
  },
];

// TODO: 백엔드 크롤링 API가 준비되면 imageUrl과 title을 응답 데이터로 교체합니다.
