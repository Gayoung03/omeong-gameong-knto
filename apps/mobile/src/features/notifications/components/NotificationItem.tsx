import Ionicons from '@expo/vector-icons/Ionicons';
import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { AppNotification } from '../types/notification';

const ICON_SIZE = 38;

type NotificationItemProps = {
  notification: AppNotification;
};

export function NotificationItem({ notification }: NotificationItemProps) {
  const isSea = notification.tone === 'sea';

  return (
    <View style={[styles.item, notification.isRead && styles.itemRead]}>
      <View style={[styles.icon, isSea && styles.iconSea]}>
        <Ionicons color={isSea ? colors.sea : colors.primary} name={notification.icon} size={19} />
      </View>

      <View style={styles.copy}>
        <View style={styles.titleRow}>
          <Text numberOfLines={1} style={styles.title}>
            {notification.title}
          </Text>
          {!notification.isRead && <View style={styles.unreadDot} />}
        </View>
        <Text style={styles.description}>{notification.description}</Text>
        <Text style={styles.receivedAt}>{notification.receivedAt}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  copy: {
    flex: 1,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    lineHeight: 17,
    marginTop: 3,
  },
  icon: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: ICON_SIZE / 2,
    height: ICON_SIZE,
    justifyContent: 'center',
    width: ICON_SIZE,
  },
  iconSea: {
    backgroundColor: colors.seaSoftLight,
  },
  item: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm + 2,
  },
  itemRead: {
    backgroundColor: colors.neutralGray,
  },
  receivedAt: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    marginTop: spacing.xs,
  },
  title: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  unreadDot: {
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    height: 6,
    width: 6,
  },
});
