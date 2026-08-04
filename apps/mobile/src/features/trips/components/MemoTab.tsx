import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import { useTripMemos, type MemoDraft } from '../hooks/useTripMemos';
import type { Schedule } from '../types/trip';
import { formatMonthDay } from '../utils/tripFormat';
import { MemoEditModal } from './MemoEditModal';

type MemoTabProps = {
  schedules: Schedule[];
};

const DAY_COLORS = [colors.primary, colors.leaf, colors.sea, colors.basalt] as const;

const EMPTY_DRAFT: MemoDraft = { title: '', content: '' };

export function MemoTab({ schedules }: MemoTabProps) {
  const { findMemoByScheduleId, saveMemo } = useTripMemos();
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null);

  const editingMemo = editingSchedule ? findMemoByScheduleId(editingSchedule.id) : null;

  const handleSubmitMemo = (draft: MemoDraft) => {
    if (!editingSchedule) {
      return;
    }
    saveMemo(editingSchedule.id, draft);
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {schedules.map((schedule, index) => {
          const memo = findMemoByScheduleId(schedule.id);
          const dayColor = DAY_COLORS[index % DAY_COLORS.length];

          return (
            <Pressable
              accessibilityRole="button"
              key={schedule.id}
              onPress={() => setEditingSchedule(schedule)}
              style={styles.card}
            >
              <View style={styles.cardHeader}>
                <View style={[styles.dayBadge, { backgroundColor: dayColor }]}>
                  <Text style={styles.dayBadgeText}>Day {schedule.dayNumber}</Text>
                </View>
                <Text style={styles.dateText}>{formatMonthDay(schedule.date)}</Text>
              </View>

              {memo ? (
                <>
                  <Text style={styles.memoTitle}>{memo.title}</Text>
                  <Text style={styles.memoContent}>{memo.content}</Text>
                </>
              ) : (
                <View style={styles.emptyRow}>
                  <Ionicons color={colors.textTertiary} name="create-outline" size={15} />
                  <Text style={styles.emptyText}>메모를 남겨보세요</Text>
                </View>
              )}
            </Pressable>
          );
        })}
      </ScrollView>

      <MemoEditModal
        dayLabel={editingSchedule ? `Day ${editingSchedule.dayNumber}` : ''}
        initialDraft={
          editingMemo ? { title: editingMemo.title, content: editingMemo.content } : EMPTY_DRAFT
        }
        isVisible={editingSchedule !== null}
        onClose={() => setEditingSchedule(null)}
        onSubmit={handleSubmitMemo}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: spacing.xl,
    paddingTop: spacing.md,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.xs + 1,
    marginBottom: spacing.sm + 2,
    marginHorizontal: spacing.lg - 2,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 4,
  },
  cardHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  dayBadge: {
    borderRadius: radius.sm + 1,
    paddingHorizontal: spacing.sm + 1,
    paddingVertical: 3,
  },
  dayBadgeText: {
    color: colors.surface,
    fontSize: typography.micro.fontSize,
    fontWeight: '700',
  },
  dateText: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  memoTitle: {
    color: colors.basalt,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
    marginTop: spacing.xs,
  },
  memoContent: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize + 0.5,
    lineHeight: 20,
  },
  emptyRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs + 2,
    marginTop: spacing.xs,
  },
  emptyText: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
  },
});
