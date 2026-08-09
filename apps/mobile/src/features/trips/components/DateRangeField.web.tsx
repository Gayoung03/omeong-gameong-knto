import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type DateRangeFieldProps = {
  startDate: string;
  endDate: string;
  onChangeRange: (startDate: string, endDate: string) => void;
};

/**
 * 웹 전용 구현.
 * @react-native-community/datetimepicker 는 웹을 지원하지 않아 브라우저 기본 날짜 입력을 사용한다.
 */
export function DateRangeField({ startDate, endDate, onChangeRange }: DateRangeFieldProps) {
  return (
    <View style={styles.row}>
      <input
        max={endDate}
        onChange={(event) => onChangeRange(event.target.value, endDate)}
        style={webInputStyle}
        type="date"
        value={startDate}
      />

      <Text style={styles.tilde}>~</Text>

      <input
        min={startDate}
        onChange={(event) => onChangeRange(startDate, event.target.value)}
        style={webInputStyle}
        type="date"
        value={endDate}
      />
    </View>
  );
}

const webInputStyle = {
  backgroundColor: colors.surface,
  border: `1px solid ${colors.border}`,
  borderRadius: `${radius.sm}px`,
  color: colors.basalt,
  fontFamily: 'inherit',
  fontSize: `${typography.label.fontSize}px`,
  fontWeight: 700,
  padding: '7px 10px',
} as const;

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  tilde: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
  },
});
