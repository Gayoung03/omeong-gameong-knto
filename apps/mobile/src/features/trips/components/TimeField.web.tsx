import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type TimeFieldProps = {
  value: string | null;
  onChangeValue: (value: string | null) => void;
};

/**
 * 웹 전용 구현.
 * @react-native-community/datetimepicker 는 웹을 지원하지 않아 브라우저 기본 시간 입력을 사용한다.
 */
export function TimeField({ value, onChangeValue }: TimeFieldProps) {
  return (
    <View style={styles.row}>
      <input
        onChange={(event) => onChangeValue(event.target.value === '' ? null : event.target.value)}
        step={300}
        style={webInputStyle}
        type="time"
        value={value ?? ''}
      />

      {value !== null && (
        <Pressable
          accessibilityRole="button"
          onPress={() => onChangeValue(null)}
          style={styles.clearButton}
        >
          <Text style={styles.clearText}>시간 지우기</Text>
        </Pressable>
      )}
    </View>
  );
}

const webInputStyle = {
  backgroundColor: colors.surface,
  border: `1px solid ${colors.border}`,
  borderRadius: `${radius.sm}px`,
  color: colors.basalt,
  fontFamily: 'inherit',
  fontSize: `${typography.label.fontSize + 1}px`,
  fontWeight: 700,
  padding: '8px 12px',
} as const;

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
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
});
