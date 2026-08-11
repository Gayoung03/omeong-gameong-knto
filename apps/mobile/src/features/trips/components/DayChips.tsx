import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { Schedule } from '../types/trip';
import { formatMonthDay } from '../utils/tripFormat';

type DayChipsProps = {
  schedules: Schedule[];
  selectedScheduleId: string;
  onSelectSchedule: (scheduleId: string) => void;
};

export function DayChips({ schedules, selectedScheduleId, onSelectSchedule }: DayChipsProps) {
  return (
    <ScrollView
      contentContainerStyle={styles.content}
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.container}
    >
      {schedules.map((schedule) => {
        const isSelected = schedule.id === selectedScheduleId;

        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: isSelected }}
            key={schedule.id}
            onPress={() => onSelectSchedule(schedule.id)}
            style={[styles.chip, isSelected && styles.selectedChip]}
          >
            <Text style={[styles.dayLabel, isSelected && styles.selectedText]}>
              Day {schedule.dayNumber}
            </Text>
            <Text style={[styles.dateLabel, isSelected && styles.selectedText]}>
              {formatMonthDay(schedule.date)}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 0,
    marginTop: spacing.sm + 4,
  },
  content: {
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  chip: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    minWidth: 78,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.xs + 2,
  },
  selectedChip: {
    backgroundColor: colors.leaf,
    borderColor: colors.leaf,
  },
  dayLabel: {
    color: colors.textPrimary,
    fontSize: typography.caption.fontSize + 1,
    fontWeight: '700',
  },
  dateLabel: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize - 1,
  },
  selectedText: {
    color: colors.surface,
  },
});
