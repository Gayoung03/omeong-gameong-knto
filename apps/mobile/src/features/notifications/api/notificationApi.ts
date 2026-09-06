import type Ionicons from '@expo/vector-icons/Ionicons';

import { apiClient } from '@/src/services/apiClient';
import { relativeTime } from '@/src/utils/relativeTime';

import type { AppNotification, NotificationType } from '../types/notification';

type NotificationResponse = {
  id: string;
  type: NotificationType;
  targetId: string | null;
  title: string;
  content: string;
  isRead: boolean;
  createdAt: string;
  readAt: string | null;
};

const ICONS: Record<NotificationType, keyof typeof Ionicons.glyphMap> = {
  chat_answer_ready: 'chatbubble-outline',
  inquiry_answered: 'chatbubble-outline',
  route_ready: 'map-outline',
  notice: 'megaphone-outline',
  travel_log_ready: 'image-outline',
};

export async function fetchNotifications(): Promise<AppNotification[]> {
  const { data } = await apiClient.get<{ items: NotificationResponse[] }>('/notifications');
  return data.items.map((item, index) => ({
    id: item.id,
    type: item.type,
    targetId: item.targetId,
    icon: ICONS[item.type] ?? 'notifications-outline',
    tone: index % 2 === 0 ? 'primary' : 'sea',
    title: item.title,
    description: item.content,
    receivedAt: relativeTime(item.createdAt),
    isRead: item.isRead,
  }));
}

export async function markNotificationRead(id: string): Promise<void> {
  await apiClient.patch(`/notifications/${id}/read`);
}
