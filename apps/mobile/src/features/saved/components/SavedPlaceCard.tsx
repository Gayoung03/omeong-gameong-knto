import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { colors, radius, spacing, typography } from '@/src/theme';

import type { SavedPlace } from '../types/saved';

type SavedPlaceCardProps = {
  onPressRemove: () => void;
  place: SavedPlace;
};

export function SavedPlaceCard({ onPressRemove, place }: SavedPlaceCardProps) {
  return (
    <View style={styles.card}>
      <RemoteImage style={styles.thumbnail} uri={place.imageUrl ?? undefined} />

      <View style={styles.info}>
        <Text numberOfLines={1} style={styles.name}>
          {place.name}
        </Text>
        <Text numberOfLines={1} style={styles.address}>
          {place.address}
        </Text>
        <Text style={styles.category}>{place.category}</Text>
      </View>

      <Pressable
        accessibilityLabel="저장 해제"
        accessibilityRole="button"
        hitSlop={10}
        onPress={onPressRemove}
        style={({ pressed }) => pressed && styles.pressed}
      >
        <Ionicons color={colors.primary} name="heart" size={20} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  address: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    marginTop: 2,
  },
  card: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm + 2,
    padding: spacing.sm + 2,
  },
  category: {
    color: colors.leaf,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
    marginTop: spacing.xs,
  },
  info: {
    flex: 1,
    minWidth: 0,
  },
  name: {
    color: colors.basalt,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  pressed: {
    opacity: 0.6,
  },
  thumbnail: {
    height: 58,
    width: 58,
  },
});
