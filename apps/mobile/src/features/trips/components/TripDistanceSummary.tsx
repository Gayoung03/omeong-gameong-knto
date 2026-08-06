import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { TripDistanceSummary as TripDistanceSummaryType } from '../types/trip';
import { formatDuration } from '../utils/tripFormat';

type TripDistanceSummaryProps = {
  summary: TripDistanceSummaryType;
};

export function TripDistanceSummary({ summary }: TripDistanceSummaryProps) {
  const stats = [
    { key: 'total', value: `${summary.totalDistanceKm} km`, label: '총 이동거리' },
    { key: 'car', value: formatDuration(summary.carMinutes), label: '차량 이동' },
    { key: 'walk', value: formatDuration(summary.walkMinutes), label: '도보 이동' },
  ];

  return (
    <View style={styles.container}>
      {stats.map((stat, index) => (
        <View key={stat.key} style={[styles.stat, index > 0 && styles.dividedStat]}>
          <Text style={styles.value}>{stat.value}</Text>
          <Text style={styles.label}>{stat.label}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md + 2,
    borderWidth: 1,
    flexDirection: 'row',
    marginHorizontal: spacing.md,
    marginTop: spacing.sm + 2,
    paddingVertical: spacing.sm,
  },
  stat: {
    alignItems: 'center',
    flex: 1,
    gap: 1,
  },
  dividedStat: {
    borderLeftColor: colors.border,
    borderLeftWidth: 1,
  },
  value: {
    color: colors.basalt,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  label: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize - 1,
  },
});
