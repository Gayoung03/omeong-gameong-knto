import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { SavedRoute } from '../types/saved';

type SavedRouteCardProps = {
  onPressRemove: () => void;
  route: SavedRoute;
};

export function SavedRouteCard({ onPressRemove, route }: SavedRouteCardProps) {
  const firstPlaceNames = route.days
    .flatMap((day) => day.places.map((place) => place.name))
    .slice(0, 3)
    .join(' · ');

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text numberOfLines={1} style={styles.title}>
          {route.title}
        </Text>
        <Pressable
          accessibilityLabel="저장 해제"
          accessibilityRole="button"
          hitSlop={10}
          onPress={onPressRemove}
          style={({ pressed }) => pressed && styles.pressed}
        >
          <Ionicons color={colors.textTertiary} name="close" size={18} />
        </Pressable>
      </View>

      <View style={styles.metaRow}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{route.duration}</Text>
        </View>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>장소 {route.placeCount}곳</Text>
        </View>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{route.petName}와 함께</Text>
        </View>
      </View>

      {firstPlaceNames ? (
        <Text numberOfLines={2} style={styles.places}>
          {firstPlaceNames}
          {route.placeCount > 3 ? ` 외 ${route.placeCount - 3}곳` : ''}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  badgeText: {
    color: colors.primaryInk,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs + 2,
  },
  places: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    lineHeight: 18,
  },
  pressed: {
    opacity: 0.6,
  },
  title: {
    color: colors.basalt,
    flex: 1,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: '700',
  },
});
