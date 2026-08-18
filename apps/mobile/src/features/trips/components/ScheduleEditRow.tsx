import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { ScheduleItem } from '../types/trip';
import { PetPolicyBadge } from './PetPolicyBadge';

type ScheduleEditRowProps = {
  item: ScheduleItem;
  /** 드래그 중인 행인지 */
  isActive: boolean;
  /** 길게 눌러 드래그를 시작 */
  onDragStart: () => void;
  onPressMore: (itemId: string) => void;
};

export function ScheduleEditRow({
  item,
  isActive,
  onDragStart,
  onPressMore,
}: ScheduleEditRowProps) {
  return (
    <View style={[styles.row, isActive && styles.activeRow]}>
      <Pressable
        accessibilityHint="길게 눌러 위아래로 끌면 순서가 바뀌어요"
        accessibilityLabel={`${item.place.name} 순서 변경`}
        accessibilityRole="button"
        delayLongPress={150}
        hitSlop={spacing.sm}
        onLongPress={onDragStart}
        style={styles.dragHandle}
      >
        <Ionicons color={colors.textTertiary} name="reorder-three" size={22} />
      </Pressable>

      <View style={styles.orderBadge}>
        <Text style={styles.orderText}>{item.order}</Text>
      </View>

      <View style={styles.body}>
        <Text numberOfLines={1} style={styles.placeName}>
          {item.place.name}
        </Text>
        <PetPolicyBadge petPolicy={item.place.petPolicy} />
      </View>

      <Pressable
        accessibilityLabel={`${item.place.name} 더보기`}
        accessibilityRole="button"
        hitSlop={spacing.sm}
        onPress={() => onPressMore(item.id)}
        style={styles.moreButton}
      >
        <Ionicons color={colors.textSecondary} name="ellipsis-vertical" size={18} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md + 2,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.sm,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.sm + 2,
  },
  activeRow: {
    borderColor: colors.primary,
    elevation: 4,
    shadowColor: colors.basalt,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
  },
  dragHandle: {
    paddingRight: spacing.xs,
  },
  orderBadge: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    height: 24,
    justifyContent: 'center',
    width: 24,
  },
  orderText: {
    color: colors.surface,
    fontSize: typography.micro.fontSize,
    fontWeight: '700',
  },
  body: {
    alignItems: 'flex-start',
    flex: 1,
    gap: spacing.xs,
  },
  placeName: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
  },
  moreButton: {
    paddingLeft: spacing.xs,
  },
});
