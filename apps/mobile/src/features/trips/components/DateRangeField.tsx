import DateTimePicker from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import { formatMonthDay, parseDate, toDateValue } from '../utils/tripFormat';

type DateRangeFieldProps = {
  startDate: string;
  endDate: string;
  onChangeRange: (startDate: string, endDate: string) => void;
};

type PickerTarget = 'start' | 'end';

export function DateRangeField({ startDate, endDate, onChangeRange }: DateRangeFieldProps) {
  const [pickerTarget, setPickerTarget] = useState<PickerTarget | null>(null);

  const handleChangeDate = (_event: unknown, selectedDate?: Date) => {
    const target = pickerTarget;

    if (Platform.OS !== 'ios') {
      setPickerTarget(null);
    }

    if (!selectedDate || !target) {
      return;
    }

    const nextValue = toDateValue(selectedDate);

    if (target === 'start') {
      onChangeRange(nextValue, endDate);
    } else {
      onChangeRange(startDate, nextValue);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <Pressable
          accessibilityRole="button"
          onPress={() => setPickerTarget('start')}
          style={[styles.dateButton, pickerTarget === 'start' && styles.activeButton]}
        >
          <Text style={styles.dateText}>{formatMonthDay(startDate)}</Text>
        </Pressable>

        <Text style={styles.tilde}>~</Text>

        <Pressable
          accessibilityRole="button"
          onPress={() => setPickerTarget('end')}
          style={[styles.dateButton, pickerTarget === 'end' && styles.activeButton]}
        >
          <Text style={styles.dateText}>{formatMonthDay(endDate)}</Text>
        </Pressable>
      </View>

      {pickerTarget !== null && (
        <View style={styles.pickerBox}>
          <DateTimePicker
            display={Platform.OS === 'ios' ? 'inline' : 'default'}
            minimumDate={pickerTarget === 'end' ? parseDate(startDate) : undefined}
            mode="date"
            onChange={handleChangeDate}
            value={parseDate(pickerTarget === 'start' ? startDate : endDate)}
          />

          {Platform.OS === 'ios' && (
            <Pressable
              accessibilityRole="button"
              onPress={() => setPickerTarget(null)}
              style={styles.confirmButton}
            >
              <Text style={styles.confirmText}>확인</Text>
            </Pressable>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.sm,
  },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  dateButton: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.sm,
    borderWidth: 1,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.xs + 3,
  },
  activeButton: {
    borderColor: colors.primary,
  },
  dateText: {
    color: colors.basalt,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  tilde: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
  },
  pickerBox: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    padding: spacing.xs,
  },
  confirmButton: {
    alignSelf: 'flex-end',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  confirmText: {
    color: colors.primary,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
});
