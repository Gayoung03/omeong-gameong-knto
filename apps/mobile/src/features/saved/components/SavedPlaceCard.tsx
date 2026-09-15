import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View, type GestureResponderEvent } from 'react-native';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { colors, radius, spacing, typography } from '@/src/theme';

import type { SavedPlace } from '../types/saved';

type SavedPlaceCardProps = {
  onPress: () => void;
  onPressRemove: () => void;
  place: SavedPlace;
};

export function SavedPlaceCard({ onPress, onPressRemove, place }: SavedPlaceCardProps) {
  const handlePressRemove = (event: GestureResponderEvent) => {
    // 하트를 누른 경우 카드의 상세 이동까지 연속으로 실행되지 않게 한다.
    event.stopPropagation();
    onPressRemove();
  };

  return (
    <Pressable
      accessibilityLabel={`${place.name} 상세 보기`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
    >
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
        onPress={handlePressRemove}
        style={({ pressed }) => pressed && styles.pressed}
      >
        <Ionicons color={colors.primary} name="heart" size={20} />
      </Pressable>
    </Pressable>
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
  cardPressed: {
    opacity: 0.68,
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
