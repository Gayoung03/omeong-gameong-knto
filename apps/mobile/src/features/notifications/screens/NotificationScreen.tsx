import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, spacing } from '@/src/theme';

import { NotificationItem } from '../components/NotificationItem';
import { appNotifications } from '../mocks/notification.mock';

export function NotificationScreen() {
  // TODO: 알림 API 가 준비되면 TanStack Query 훅으로 교체한다.
  const notifications = appNotifications;

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="알림" />

      {notifications.length === 0 ? (
        <EmptyState
          description="여행 일정과 날씨 소식이 도착하면 여기에 모아드릴게요."
          icon="notifications-outline"
          title="아직 도착한 알림이 없어요"
        />
      ) : (
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.list}>
            {notifications.map((notification) => (
              <NotificationItem key={notification.id} notification={notification} />
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
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});
