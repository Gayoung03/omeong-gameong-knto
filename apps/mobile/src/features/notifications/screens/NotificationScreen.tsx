import { useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, spacing } from '@/src/theme';

import { NotificationItem } from '../components/NotificationItem';
import { markNotificationRead } from '../api/notificationApi';
import { useNotifications } from '../hooks/useNotifications';
import { openNotification } from '../services/pushNotifications';
import type { AppNotification } from '../types/notification';

export function NotificationScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: notifications = [], isLoading } = useNotifications();

  const handlePress = (notification: AppNotification) => {
    openNotification(router, notification.type, notification.targetId);
    if (!notification.isRead) {
      void markNotificationRead(notification.id).then(() =>
        queryClient.invalidateQueries({ queryKey: ['notifications'] }),
      );
    }
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="알림" />

      {isLoading ? (
        <ActivityIndicator color={colors.primary} style={styles.loading} />
      ) : notifications.length === 0 ? (
        <EmptyState
          description="여행 일정과 날씨 소식이 도착하면 여기에 모아드릴게요."
          icon="notifications-outline"
          title="아직 도착한 알림이 없어요"
        />
      ) : (
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.list}>
            {notifications.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onPress={() => handlePress(notification)}
              />
            ))}
          </View>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
  },
  list: {
    gap: spacing.sm,
  },
  loading: {
    marginTop: spacing.xl,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});
