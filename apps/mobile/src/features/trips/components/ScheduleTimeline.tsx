import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { Schedule } from '../types/trip';
import { ScheduleTimelineItem } from './ScheduleTimelineItem';

type ScheduleTimelineProps = {
  schedule: Schedule;
  onPressItem: (placeId: string) => void;
  onToggleSave: (scheduleItemId: string) => void;
};

export function ScheduleTimeline({ schedule, onPressItem, onToggleSave }: ScheduleTimelineProps) {
  if (schedule.items.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyTitle}>아직 등록한 일정이 없어요</Text>
        <Text style={styles.emptyDescription}>아래 일정 추가 버튼으로 첫 장소를 담아보세요.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {schedule.items.map((item, index) => (
        <ScheduleTimelineItem
          isLast={index === schedule.items.length - 1}
          item={item}
          key={item.id}
          onPressItem={onPressItem}
          onToggleSave={onToggleSave}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  empty: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs,
    marginHorizontal: spacing.md,
    paddingVertical: spacing.xl,
  },
  emptyTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  emptyDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
});
