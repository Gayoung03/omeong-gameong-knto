import type Ionicons from '@expo/vector-icons/Ionicons';

export type NotificationPreview = {
  id: string;
  icon: keyof typeof Ionicons.glyphMap;
  /** 아이콘 배경 톤. 귤(primary) / 바다(sea) 두 가지를 번갈아 쓴다. */
  tone: 'primary' | 'sea';
  title: string;
  description: string;
};

/**
 * 상단 바 알림 팝업에 보여줄 임시 목록.
 *
 * TODO: 백엔드 알림 API 가 준비되면 TanStack Query 훅으로 교체하고
 *       이 파일은 `src/features/notifications/mocks/` 로 옮긴다.
 */
export const notificationPreviews: NotificationPreview[] = [
  {
    id: 'weather',
    icon: 'sunny-outline',
    tone: 'primary',
    title: '제주 날씨를 확인했어요',
    description: '여행 첫날은 맑고 산책하기 좋은 날씨예요.',
  },
  {
    id: 'pet',
    icon: 'paw-outline',
    tone: 'sea',
    title: '반려동물 정보를 확인해주세요',
    description: '몽이의 체중과 크기를 언제든 수정할 수 있어요.',
  },
];
