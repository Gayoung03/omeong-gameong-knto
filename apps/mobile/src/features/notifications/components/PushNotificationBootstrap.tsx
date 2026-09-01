import * as Notifications from 'expo-notifications';
import { useRouter } from 'expo-router';
import { useEffect } from 'react';
import { Platform } from 'react-native';

import type { NotificationType } from '../types/notification';
import { openNotification, registerPushToken } from '../services/pushNotifications';

export function PushNotificationBootstrap() {
  const router = useRouter();

  useEffect(() => {
    void registerPushToken().catch(() => undefined);
    if (Platform.OS === 'web') return;

    const open = (response: Notifications.NotificationResponse) => {
      const data = response.notification.request.content.data ?? {};
      openNotification(
        router,
        data.type as NotificationType | undefined,
        data.targetId as string | null,
      );
    };
    const subscription = Notifications.addNotificationResponseReceivedListener(open);
    void Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) {
        open(response);
        void Notifications.clearLastNotificationResponseAsync();
      }
    });
    return () => subscription.remove();
  }, [router]);

  return null;
}
