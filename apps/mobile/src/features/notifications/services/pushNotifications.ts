import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import { type Href, useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

import { apiClient } from '@/src/services/apiClient';

import type { NotificationType } from '../types/notification';

type Router = ReturnType<typeof useRouter>;
const PUSH_TOKEN_KEY = 'omeong-gameong.expo-push-token';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function registerPushToken(): Promise<void> {
  if (Platform.OS === 'web') return;
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: '기본 알림',
      importance: Notifications.AndroidImportance.DEFAULT,
    });
  }

  const current = await Notifications.getPermissionsAsync();
  const permission = current.granted ? current : await Notifications.requestPermissionsAsync();
  if (!permission.granted) return;

  const projectId = Constants.easConfig?.projectId ?? Constants.expoConfig?.extra?.eas?.projectId;
  if (!projectId) return;

  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  await apiClient.post('/push-tokens', { token, platform: Platform.OS });
  await AsyncStorage.setItem(PUSH_TOKEN_KEY, token);
}

export async function unregisterPushToken(): Promise<void> {
  const token = await AsyncStorage.getItem(PUSH_TOKEN_KEY);
  if (!token) return;
  try {
    await apiClient.delete('/push-tokens', { data: { token } });
  } finally {
    await AsyncStorage.removeItem(PUSH_TOKEN_KEY);
  }
}

export function openNotification(
  router: Router,
  type?: NotificationType,
  targetId?: string | null,
) {
  const paths: Partial<Record<NotificationType, Href>> = {
    chat_answer_ready: '/chatbot',
    inquiry_answered: targetId ? (`/inquiries/${targetId}` as Href) : '/inquiries',
    notice: '/notices',
    route_ready: targetId ? (`/trips/${targetId}` as Href) : '/trips',
    travel_log_ready: '/travel-logs',
  };
  router.push(paths[type ?? 'notice'] ?? '/notifications');
}
