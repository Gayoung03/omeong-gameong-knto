import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { TripListItem } from '../types/trip';
import { formatTripPeriod } from '../utils/tripFormat';

type TripListCardProps = {
  trip: TripListItem;
  onPress: () => void;
  onDelete: () => void;
  isDeleting?: boolean;
};

export function TripListCard({ trip, onPress, onDelete, isDeleting }: TripListCardProps) {
  return (
    <View style={styles.card}>
      <Pressable
        accessibilityHint="여행 일정을 확인할 수 있어요"
        accessibilityRole="button"
        onPress={onPress}
        style={({ pressed }) => [styles.openArea, pressed && styles.pressed]}
      >
        <View style={styles.emojiBox}>
          <Text style={styles.emoji}>{trip.coverEmoji}</Text>
        </View>

        <View style={styles.body}>
          <Text numberOfLines={1} style={styles.title}>
            {trip.title}
          </Text>
          <Text style={styles.period}>{formatTripPeriod(trip)}</Text>
        </View>

        <Ionicons color={colors.textTertiary} name="chevron-forward" size={18} />
      </Pressable>
      <Pressable
        accessibilityLabel={`${trip.title} 삭제`}
        accessibilityRole="button"
        disabled={isDeleting}
        hitSlop={8}
        onPress={onDelete}
        style={({ pressed }) => [styles.deleteButton, pressed && styles.pressed]}
      >
        <Ionicons color={colors.error} name="trash-outline" size={20} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  body: {
    flex: 1,
    gap: 2,
  },
  card: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: 'row',
    paddingRight: spacing.md,
  },
  deleteButton: {
    alignItems: 'center',
    borderRadius: radius.full,
    height: 40,
    justifyContent: 'center',
    marginLeft: spacing.xs,
    width: 40,
  },
  emoji: {
    fontSize: 24,
  },
  emojiBox: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.md,
    height: 48,
    justifyContent: 'center',
    width: 48,
  },
  period: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
  openArea: {
    alignItems: 'center',
    flex: 1,
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.md,
    paddingRight: spacing.xs,
  },
  pressed: {
    opacity: 0.7,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
});
