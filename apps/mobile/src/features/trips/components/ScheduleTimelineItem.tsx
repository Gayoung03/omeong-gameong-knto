import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { ScheduleItem } from '../types/trip';
import { formatMoveInfo } from '../utils/tripFormat';
import { PetPolicyBadge } from './PetPolicyBadge';

type ScheduleTimelineItemProps = {
  item: ScheduleItem;
  isLast: boolean;
  onPressItem: (placeId: string) => void;
  onToggleSave: (scheduleItemId: string) => void;
};

const ORDER_COLORS = [colors.primary, colors.leaf, colors.sea, colors.basalt] as const;

function getOrderColor(order: number): string {
  return ORDER_COLORS[(order - 1) % ORDER_COLORS.length];
}

export function ScheduleTimelineItem({
  item,
  isLast,
  onPressItem,
  onToggleSave,
}: ScheduleTimelineItemProps) {
  return (
    <View style={styles.row}>
      <View style={styles.rail}>
        <View style={[styles.orderBadge, { backgroundColor: getOrderColor(item.order) }]}>
          <Text style={styles.orderText}>{item.order}</Text>
        </View>
        {!isLast && <View style={styles.railLine} />}
      </View>

      <View style={styles.body}>
        <Pressable
          accessibilityRole="button"
          onPress={() => onPressItem(item.place.id)}
          style={styles.card}
        >
          <View style={styles.cardHeader}>
            <Text numberOfLines={1} style={styles.placeName}>
              {item.place.name}
            </Text>
            <Pressable
              accessibilityLabel={item.isSaved ? '저장 해제' : '저장'}
              accessibilityRole="button"
              hitSlop={spacing.sm}
              onPress={() => onToggleSave(item.id)}
            >
              <Ionicons
                color={item.isSaved ? colors.primary : colors.textTertiary}
                name={item.isSaved ? 'star' : 'star-outline'}
                size={16}
              />
            </Pressable>
          </View>

          <PetPolicyBadge petPolicy={item.place.petPolicy} />

          <Text numberOfLines={2} style={styles.description}>
            {item.place.description}
          </Text>
        </Pressable>

        {item.moveToNext && (
          <Text style={styles.moveInfo}>
            ↓{' '}
            {formatMoveInfo(
              item.moveToNext.transport,
              item.moveToNext.distanceMeters,
              item.moveToNext.durationMinutes,
            )}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.sm + 4,
  },
  rail: {
    alignItems: 'center',
    width: 26,
  },
  orderBadge: {
    alignItems: 'center',
    borderRadius: radius.full,
    height: 24,
    justifyContent: 'center',
    width: 24,
  },
  orderText: {
    color: colors.surface,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
  railLine: {
    backgroundColor: colors.border,
    flex: 1,
    width: 2,
  },
  body: {
    flex: 1,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md + 2,
    borderWidth: 1,
    gap: spacing.xs + 1,
    paddingHorizontal: spacing.sm + 4,
    paddingVertical: spacing.sm + 2,
  },
  cardHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
  },
  placeName: {
    color: colors.basalt,
    flex: 1,
    fontSize: typography.subtitle.fontSize - 1,
    fontWeight: typography.subtitle.fontWeight,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
  moveInfo: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
    paddingVertical: spacing.xs + 2,
  },
});
