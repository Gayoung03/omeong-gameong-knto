import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { ScheduleItem } from '../types/trip';
import { formatMoveInfo, formatTimeLabel } from '../utils/tripFormat';
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
            {item.startTime && (
              <Text style={styles.startTime}>{formatTimeLabel(item.startTime)}</Text>
            )}
            <Text numberOfLines={1} style={styles.placeName}>
              {item.place.name}
            </Text>
            {/* 저장 버튼이 앉을 자리. 실제 버튼은 카드 Pressable 바깥에 있다 */}
            <View style={styles.saveSlot} />
          </View>

          <PetPolicyBadge petPolicy={item.place.petPolicy} />

          <Text numberOfLines={2} style={styles.description}>
            {item.place.description}
          </Text>

          {item.memo.length > 0 && (
            <View style={styles.memoRow}>
              <Ionicons color={colors.textTertiary} name="create-outline" size={12} />
              <Text numberOfLines={2} style={styles.memo}>
                {item.memo}
              </Text>
            </View>
          )}
        </Pressable>

        {/*
          웹에서 <button> 안에 <button> 이 들어가면 안 되므로 카드 Pressable 의
          자식이 아니라 형제로 두고, 원래 자리에 겹쳐 놓는다.
        */}
        <Pressable
          accessibilityLabel={item.isSaved ? '저장 해제' : '저장'}
          accessibilityRole="button"
          onPress={() => onToggleSave(item.id)}
          style={styles.saveButton}
        >
          <Ionicons
            color={item.isSaved ? colors.primary : colors.textTertiary}
            name={item.isSaved ? 'star' : 'star-outline'}
            size={16}
          />
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
  saveSlot: {
    height: 16,
    width: 16,
  },
  saveButton: {
    padding: spacing.sm,
    position: 'absolute',
    right: spacing.xs,
    top: spacing.xs,
  },
  cardHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
  },
  startTime: {
    backgroundColor: colors.basaltSoft,
    borderRadius: radius.sm,
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
    overflow: 'hidden',
    paddingHorizontal: spacing.xs + 2,
    paddingVertical: 2,
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
  memoRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.xs,
    marginTop: 1,
  },
  memo: {
    color: colors.textTertiary,
    flex: 1,
    fontSize: typography.micro.fontSize,
    lineHeight: 15,
  },
  moveInfo: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
    paddingVertical: spacing.xs + 2,
  },
});
