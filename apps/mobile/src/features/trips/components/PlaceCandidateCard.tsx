import Ionicons from '@expo/vector-icons/Ionicons';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { PlaceCandidate } from '../types/trip';
import { formatPlaceMeta, formatRating, formatSavedCount } from '../utils/tripFormat';
import { PetPolicyBadge } from './PetPolicyBadge';

type PlaceCandidateCardProps = {
  place: PlaceCandidate;
  /** 지도에서 선택된 장소인지 */
  isSelected: boolean;
  /** 이번에 이미 일정에 담은 장소인지 */
  isAdded: boolean;
  onPress: (placeId: string) => void;
  onPressSelect: (place: PlaceCandidate) => void;
};

/** 일정 추가 화면의 장소 후보 한 줄 */
export function PlaceCandidateCard({
  place,
  isSelected,
  isAdded,
  onPress,
  onPressSelect,
}: PlaceCandidateCardProps) {
  const ratingText = formatRating(place.rating, place.reviewCount);

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: isSelected }}
      onPress={() => onPress(place.id)}
      style={[styles.row, isSelected && styles.selectedRow]}
    >
      {place.imageUrl ? (
        <Image source={{ uri: place.imageUrl }} style={styles.thumbnail} />
      ) : (
        <View style={[styles.thumbnail, styles.thumbnailPlaceholder]}>
          <Ionicons color={colors.textTertiary} name="image-outline" size={20} />
        </View>
      )}

      <View style={styles.body}>
        <Text numberOfLines={1} style={styles.name}>
          {place.name}
        </Text>

        <Text numberOfLines={2} style={styles.description}>
          {place.description}
        </Text>

        <View style={styles.statsRow}>
          {ratingText && (
            <>
              <Ionicons color={colors.warning} name="star" size={12} />
              <Text style={styles.statsText}>{ratingText}</Text>
            </>
          )}
          {ratingText && place.savedCount > 0 && <Text style={styles.statsDot}>·</Text>}
          {place.savedCount > 0 && (
            <Text style={styles.statsText}>{formatSavedCount(place.savedCount)}</Text>
          )}
        </View>

        <Text style={styles.meta}>{formatPlaceMeta(place.category, place.regionLabel)}</Text>

        <PetPolicyBadge petPolicy={place.petPolicy} />
      </View>

      <Pressable
        accessibilityLabel={`${place.name} 일정에 담기`}
        accessibilityRole="button"
        disabled={isAdded}
        onPress={() => onPressSelect(place)}
        style={[styles.selectButton, isAdded && styles.addedButton]}
      >
        <Text style={[styles.selectText, isAdded && styles.addedText]}>
          {isAdded ? '담김' : '선택'}
        </Text>
      </Pressable>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm + 4,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md - 2,
  },
  selectedRow: {
    backgroundColor: colors.primarySoft,
  },
  thumbnail: {
    backgroundColor: colors.basaltSoft,
    borderRadius: radius.md,
    height: 76,
    width: 76,
  },
  thumbnailPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: {
    alignItems: 'flex-start',
    flex: 1,
    gap: 3,
  },
  name: {
    color: colors.basalt,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    lineHeight: 17,
  },
  statsRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 3,
  },
  statsText: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  statsDot: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
  },
  meta: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
  },
  selectButton: {
    alignItems: 'center',
    alignSelf: 'center',
    backgroundColor: colors.basaltSoft,
    borderRadius: radius.full,
    minWidth: 56,
    paddingHorizontal: spacing.md - 2,
    paddingVertical: spacing.sm,
  },
  addedButton: {
    backgroundColor: colors.leafSoft,
  },
  selectText: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  addedText: {
    color: colors.leaf,
  },
});
