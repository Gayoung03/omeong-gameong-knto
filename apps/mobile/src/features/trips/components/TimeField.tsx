import DateTimePicker from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import { formatTimeLabel, parseTimeValue, toTimeValue } from '../utils/tripFormat';

type TimeFieldProps = {
  /** 'HH:mm'. 정하지 않았으면 null */
  value: string | null;
  onChangeValue: (value: string | null) => void;
};

/** 방문 시각 입력. 시간을 정하지 않는 것도 허용한다 */
export function TimeField({ value, onChangeValue }: TimeFieldProps) {
  const [isPickerOpen, setIsPickerOpen] = useState(false);

  const handleChangeTime = (_event: unknown, selectedDate?: Date) => {
    if (Platform.OS !== 'ios') {
      setIsPickerOpen(false);
    }

    if (!selectedDate) {
      return;
    }

    onChangeValue(toTimeValue(selectedDate));
  };

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <Pressable
          accessibilityRole="button"
          onPress={() => setIsPickerOpen(true)}
          style={[styles.timeButton, isPickerOpen && styles.activeButton]}
        >
          <Text style={[styles.timeText, value === null && styles.emptyText]}>
            {value === null ? '시간 미정' : formatTimeLabel(value)}
          </Text>
        </Pressable>

        {value !== null && (
          <Pressable
            accessibilityRole="button"
            onPress={() => {
              setIsPickerOpen(false);
              onChangeValue(null);
            }}
            style={styles.clearButton}
          >
            <Text style={styles.clearText}>시간 지우기</Text>
          </Pressable>
        )}
      </View>

      {isPickerOpen && (
        <View style={styles.pickerBox}>
          <DateTimePicker
            display={Platform.OS === 'ios' ? 'spinner' : 'default'}
            minuteInterval={5}
            mode="time"
            onChange={handleChangeTime}
            value={parseTimeValue(value)}
          />

          {Platform.OS === 'ios' && (
            <Pressable
              accessibilityRole="button"
              onPress={() => {
                // 스피너를 한 번도 움직이지 않았으면 기본값을 그대로 확정한다
                if (value === null) {
                  onChangeValue(toTimeValue(parseTimeValue(null)));
                }
                setIsPickerOpen(false);
              }}
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
  timeButton: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.sm,
    borderWidth: 1,
    paddingHorizontal: spacing.md - 2,
    paddingVertical: spacing.sm + 1,
  },
  activeButton: {
    borderColor: colors.primary,
  },
  timeText: {
    color: colors.basalt,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
  },
  emptyText: {
    color: colors.textTertiary,
  },
  clearButton: {
    paddingHorizontal: spacing.xs,
    paddingVertical: spacing.xs,
  },
  clearText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
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
