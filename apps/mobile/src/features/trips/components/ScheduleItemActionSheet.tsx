import Ionicons from '@expo/vector-icons/Ionicons';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

import type { Schedule } from '../types/trip';
import { formatMonthDay } from '../utils/tripFormat';

type ScheduleItemActionSheetProps = {
  placeName: string;
  /** 이 항목이 현재 속한 날짜 */
  currentScheduleId: string;
  schedules: Schedule[];
  onMoveToSchedule: (scheduleId: string) => void;
  onRemove: () => void;
  onClose: () => void;
};

export function ScheduleItemActionSheet({
  placeName,
  currentScheduleId,
  schedules,
  onMoveToSchedule,
  onRemove,
  onClose,
}: ScheduleItemActionSheetProps) {
  const otherSchedules = schedules.filter((schedule) => schedule.id !== currentScheduleId);

  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible>
      <View style={styles.backdrop}>
        <Pressable
          accessibilityLabel="닫기"
          accessibilityRole="button"
          onPress={onClose}
          style={styles.backdropArea}
        />

        <View style={styles.sheet}>
          <View style={styles.grip} />

          <Text numberOfLines={1} style={styles.title}>
            {placeName}
          </Text>

          {otherSchedules.length > 0 ? (
            <>
              <Text style={styles.sectionLabel}>다른 날짜로 이동</Text>
              <ScrollView style={styles.moveList}>
                {otherSchedules.map((schedule) => (
                  <Pressable
                    accessibilityRole="button"
                    key={schedule.id}
                    onPress={() => onMoveToSchedule(schedule.id)}
                    style={styles.moveRow}
                  >
                    <Ionicons color={colors.leaf} name="calendar-outline" size={17} />
                    <Text style={styles.moveText}>
                      Day {schedule.dayNumber}로 이동
                      <Text style={styles.moveDate}> · {formatMonthDay(schedule.date)}</Text>
                    </Text>
                  </Pressable>
                ))}
              </ScrollView>
            </>
          ) : (
            <Text style={styles.emptyText}>옮길 수 있는 다른 날짜가 없어요</Text>
          )}

          <Pressable accessibilityRole="button" onPress={onRemove} style={styles.removeRow}>
            <Ionicons color={colors.error} name="trash-outline" size={17} />
            <Text style={styles.removeText}>일정에서 삭제</Text>
          </Pressable>

          <Pressable accessibilityRole="button" onPress={onClose} style={styles.cancelButton}>
            <Text style={styles.cancelText}>취소</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: overlayColors.scrim,
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdropArea: {
    flex: 1,
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl + 4,
    borderTopRightRadius: radius.xl + 4,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  grip: {
    alignSelf: 'center',
    backgroundColor: colors.border,
    borderRadius: radius.sm,
    height: 4,
    marginBottom: spacing.md,
    width: 40,
  },
  title: {
    color: colors.basalt,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  sectionLabel: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
    marginTop: spacing.md,
  },
  moveList: {
    maxHeight: 200,
  },
  moveRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    paddingVertical: spacing.sm + 4,
  },
  moveText: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '600',
  },
  moveDate: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '400',
  },
  emptyText: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
    paddingVertical: spacing.md,
  },
  removeRow: {
    alignItems: 'center',
    borderTopColor: colors.border,
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.xs,
    paddingTop: spacing.md,
  },
  removeText: {
    color: colors.error,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '600',
  },
  cancelButton: {
    alignItems: 'center',
    backgroundColor: colors.basaltSoft,
    borderRadius: radius.md,
    marginTop: spacing.md,
    paddingVertical: spacing.sm + 4,
  },
  cancelText: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
});
