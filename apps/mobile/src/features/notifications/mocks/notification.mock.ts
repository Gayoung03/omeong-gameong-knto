import type { AppNotification } from '../types/notification';

/**
 * 알림 목록 임시 데이터.
 *
 * 상단 바 팝업(`NotificationPopup`)은 이 목록의 앞 두 건만 보여준다.
 * TODO: 백엔드 알림 API 가 준비되면 TanStack Query 훅으로 교체한다.
 */
export const appNotifications: AppNotification[] = [
  {
    id: 'weather',
    icon: 'sunny-outline',
    tone: 'primary',
    title: '제주 날씨를 확인했어요',
    description: '여행 첫날은 맑고 산책하기 좋은 날씨예요.',
    receivedAt: '방금 전',
    isRead: false,
  },
  {
    id: 'pet',
    icon: 'paw-outline',
    tone: 'sea',
    title: '반려동물 정보를 확인해주세요',
    description: '몽이의 체중과 크기를 언제든 수정할 수 있어요.',
    receivedAt: '2시간 전',
    isRead: false,
  },
  {
    id: 'trip',
    icon: 'calendar-outline',
    tone: 'primary',
    title: '여행이 3일 남았어요',
    description: '준비물 체크리스트를 미리 확인해보세요.',
    receivedAt: '어제',
    isRead: true,
  },
  {
    id: 'place',
    icon: 'location-outline',
    tone: 'sea',
    title: '저장한 장소에 새 리뷰가 달렸어요',
    description: '카페 델문도에 반려견 동반 후기가 올라왔어요.',
    receivedAt: '3일 전',
    isRead: true,
  },
];
