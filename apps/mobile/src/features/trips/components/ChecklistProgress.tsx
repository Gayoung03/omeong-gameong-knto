import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type ChecklistProgressProps = {
  checkedCount: number;
  totalCount: number;
  progressRate: number;
};

export function ChecklistProgress({
  checkedCount,
  totalCount,
  progressRate,
}: ChecklistProgressProps) {
  const progressPercent = `${Math.round(progressRate * 100)}%` as const;

  return (
    <View style={styles.container}>
      <View style={styles.bar}>
        <View style={[styles.fill, { width: progressPercent }]} />
      </View>
      <Text style={styles.count}>
        {checkedCount} / {totalCount} 완료
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.xs + 1,
    paddingHorizontal: spacing.lg - 2,
    paddingTop: spacing.sm,
  },
  bar: {
    backgroundColor: colors.border,
    borderRadius: radius.sm,
    height: 6,
    overflow: 'hidden',
  },
  fill: {
    backgroundColor: colors.sea,
    borderRadius: radius.sm,
    height: '100%',
  },
  count: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
    textAlign: 'right',
  },
});
