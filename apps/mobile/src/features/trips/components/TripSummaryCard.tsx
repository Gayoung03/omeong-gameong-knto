import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { Trip } from '../types/trip';
import { formatTripPeriod, formatTripTags } from '../utils/tripFormat';

type TripSummaryCardProps = {
  trip: Trip;
  onPressInfo: () => void;
};

export function TripSummaryCard({ trip, onPressInfo }: TripSummaryCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.avatar}>
        <Text style={styles.avatarEmoji}>{trip.coverEmoji}</Text>
      </View>

      <View style={styles.meta}>
        <Text numberOfLines={1} style={styles.title}>
          {trip.title}
        </Text>
        <Text numberOfLines={1} style={styles.period}>
          {formatTripPeriod(trip)}
        </Text>
        <Text numberOfLines={1} style={styles.tags}>
          {formatTripTags(trip)}
        </Text>
      </View>

      <Pressable
        accessibilityRole="button"
        hitSlop={spacing.sm}
        onPress={onPressInfo}
        style={styles.infoButton}
      >
        <Text style={styles.infoButtonText}>여행 정보</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm + 2,
    marginHorizontal: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 4,
  },
  avatar: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    height: 46,
    justifyContent: 'center',
    width: 46,
  },
  avatarEmoji: {
    fontSize: 24,
  },
  meta: {
    flex: 1,
    gap: 3,
  },
  title: {
    color: colors.basalt,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  period: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
  tags: {
    color: colors.leaf,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  infoButton: {
    backgroundColor: colors.seaSoft,
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.xs + 2,
  },
  infoButtonText: {
    color: colors.sea,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
});
