import type Ionicons from '@expo/vector-icons/Ionicons';

export type NotificationTone = 'primary' | 'sea';
export type NotificationType =
  'chat_answer_ready' | 'inquiry_answered' | 'notice' | 'route_ready' | 'travel_log_ready';

export type AppNotification = {
  id: string;
  type: NotificationType;
  targetId: string | null;
  icon: keyof typeof Ionicons.glyphMap;
  /** 아이콘 배경 톤. 귤(primary) / 바다(sea) 두 가지를 번갈아 쓴다. */
  tone: NotificationTone;
  title: string;
  description: string;
  /**
   * 화면에 그대로 보여줄 상대 시간 문구.
   * TODO: API 연동 시 ISO 8601 문자열로 바꾸고 포맷 함수를 utils 에 둔다.
   */
  receivedAt: string;
  isRead: boolean;
};
