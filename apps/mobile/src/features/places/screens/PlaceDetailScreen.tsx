import Ionicons from '@expo/vector-icons/Ionicons';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PetPolicyBadge } from '@/src/components/domain/PetPolicyBadge';
import { EmptyState } from '@/src/components/feedback/EmptyState';
import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { ReviewPreviewSection } from '@/src/features/reviews/components/ReviewPreviewSection';
import { colors, radius, spacing, typography } from '@/src/theme';

import { usePlaceDetail } from '../hooks/usePlaceDetail';
import type { PlaceDetail } from '../types/placeDetail';

type PlaceDetailScreenProps = {
  placeId: string;
};

export function PlaceDetailScreen({ placeId }: PlaceDetailScreenProps) {
  const { data: place, isPending } = usePlaceDetail(placeId);

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="장소 상세" />

      {isPending ? (
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : !place ? (
        <EmptyState
          description="주소가 잘못되었거나 삭제된 장소일 수 있어요."
          icon="alert-circle-outline"
          title="장소를 찾을 수 없어요"
        />
      ) : (
        <PlaceDetailView place={place} />
      )}
    </SafeAreaView>
  );
}

function PlaceDetailView({ place }: { place: PlaceDetail }) {
  const chips = [place.region, place.environment, formatDistance(place.distanceKm)].filter(
    (value): value is string => Boolean(value),
  );

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <RemoteImage borderRadius={radius.lg} style={styles.hero} uri={place.imageUrl ?? undefined} />

      <View style={styles.titleBlock}>
        <View style={styles.titleRow}>
          <Text style={styles.name}>{place.name}</Text>
          <View style={styles.categoryBadge}>
            <Text style={styles.categoryText}>{place.categoryLabel}</Text>
          </View>
        </View>

        {(place.rating !== null || place.savedCount !== null) && (
          <View style={styles.statsRow}>
            {place.rating !== null && (
              <View style={styles.stat}>
                <Ionicons color={colors.warning} name="star" size={13} />
                <Text style={styles.statText}>
                  {place.rating.toFixed(1)}
                  {place.reviewCount !== null && ` (${place.reviewCount.toLocaleString()})`}
                </Text>
              </View>
            )}
            {place.savedCount !== null && (
              <View style={styles.stat}>
                <Ionicons color={colors.primary} name="heart" size={13} />
                <Text style={styles.statText}>{place.savedCount.toLocaleString()}</Text>
              </View>
            )}
          </View>
        )}
      </View>

      <PetSection place={place} />

      <View style={styles.card}>
        <Text style={styles.cardLabel}>주소</Text>
        <View style={styles.addressRow}>
          <Ionicons color={colors.textSecondary} name="location-outline" size={16} />
          <Text style={styles.addressText}>{place.address}</Text>
        </View>

        {chips.length > 0 && (
          <View style={styles.chipRow}>
            {chips.map((chip) => (
              <View key={chip} style={styles.chip}>
                <Text style={styles.chipText}>{chip}</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {place.description && (
        <View style={styles.card}>
          <Text style={styles.cardLabel}>소개</Text>
          <Text style={styles.description}>{place.description}</Text>
        </View>
      )}

      {place.isReservable && (
        <View style={styles.notice}>
          <Ionicons color={colors.seaDeep} name="calendar-outline" size={16} />
          <Text style={styles.noticeText}>예약이 가능한 장소예요.</Text>
        </View>
      )}

      <ReviewPreviewSection placeId={place.id} />
    </ScrollView>
  );
}

/** 동반 정책은 아는 만큼만 보여준다. 모르는 것을 아는 척하지 않는다. */
function PetSection({ place }: { place: PlaceDetail }) {
  if (place.petPolicy !== null) {
    return (
      <View style={styles.card}>
        <Text style={styles.cardLabel}>반려동물 동반</Text>
        <PetPolicyBadge petPolicy={place.petPolicy} />
      </View>
    );
  }

  if (place.petFriendly === null) {
    return null;
  }

  return (
    <View style={styles.card}>
      <Text style={styles.cardLabel}>반려동물 동반</Text>
      <View style={[styles.simpleBadge, !place.petFriendly && styles.simpleBadgeOff]}>
        <Text style={[styles.simpleBadgeText, !place.petFriendly && styles.simpleBadgeTextOff]}>
          🐾 {place.petFriendly ? '동반 가능' : '동반 불가'}
        </Text>
      </View>
      {place.petFriendly && (
        <Text style={styles.hint}>구역별 동반 조건은 방문 전에 한 번 더 확인하시는 걸 권해요.</Text>
      )}
    </View>
  );
}

function formatDistance(distanceKm: number | null): string | null {
  return distanceKm === null ? null : `현위치에서 ${distanceKm}km`;
}

const styles = StyleSheet.create({
  addressRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs + 2,
  },
  addressText: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.body.fontSize - 2,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  cardLabel: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: typography.label.fontWeight,
  },
  categoryBadge: {
    backgroundColor: colors.neutralGray,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  categoryText: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  centered: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
  },
  chip: {
    backgroundColor: colors.neutralGray,
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 4,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs + 2,
  },
  chipText: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  content: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
  },
  description: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize - 2,
    lineHeight: 22,
  },
  hero: {
    height: 200,
    width: '100%',
  },
  hint: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    lineHeight: 16,
  },
  name: {
    color: colors.basalt,
    flexShrink: 1,
    fontSize: typography.title.fontSize,
    fontWeight: '800',
  },
  notice: {
    alignItems: 'center',
    backgroundColor: colors.seaSoftLight,
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm + 4,
  },
  noticeText: {
    color: colors.seaDeep,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  simpleBadge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.leafSoft,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  simpleBadgeOff: {
    backgroundColor: colors.basaltSoft,
  },
  simpleBadgeText: {
    color: colors.leaf,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  simpleBadgeTextOff: {
    color: colors.textSecondary,
  },
  stat: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  statText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  statsRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  titleBlock: {
    gap: spacing.sm,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
});
