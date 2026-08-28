import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { ScheduleItem } from '../types/trip';
import { formatMoveInfo } from '../utils/tripFormat';
import { PetPolicyBadge } from './PetPolicyBadge';

type MapPlaceCardProps = {
  item: ScheduleItem;
  onPressDetail: (placeId: string) => void;
  onClose: () => void;
};

/** 지도에서 마커를 눌렀을 때 하단에 뜨는 장소 카드 */
export function MapPlaceCard({ item, onPressDetail, onClose }: MapPlaceCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.orderBadge}>
          <Text style={styles.orderText}>{item.order}</Text>
        </View>
        <Text numberOfLines={1} style={styles.placeName}>
          {item.place.name}
        </Text>
        <Pressable
          accessibilityLabel="닫기"
          accessibilityRole="button"
          hitSlop={spacing.sm}
          onPress={onClose}
        >
          <Ionicons color={colors.textTertiary} name="close" size={18} />
        </Pressable>
      </View>

      <View style={styles.badgeRow}>
        <PetPolicyBadge petPolicy={item.place.petPolicy} />
        {item.place.rating !== null && (
          <View style={styles.rating}>
            <Ionicons color={colors.warning} name="star" size={12} />
            <Text style={styles.ratingText}>
              {item.place.rating.toFixed(1)} ({item.place.reviewCount.toLocaleString()})
            </Text>
          </View>
        )}
      </View>

      <Text numberOfLines={2} style={styles.description}>
        {item.place.description}
      </Text>

      <Text numberOfLines={1} style={styles.address}>
        {item.place.address}
      </Text>

      {item.moveToNext && (
        <Text style={styles.moveInfo}>
          다음 일정까지{' '}
          {formatMoveInfo(
            item.moveToNext.transport,
            item.moveToNext.distanceMeters,
            item.moveToNext.durationMinutes,
          )}
        </Text>
      )}

      {!item.place.isCustom ? (
        <Pressable
          accessibilityRole="button"
          onPress={() => onPressDetail(item.place.id)}
          style={styles.detailButton}
        >
          <Text style={styles.detailText}>장소 자세히 보기</Text>
          <Ionicons color={colors.primary} name="chevron-forward" size={14} />
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    elevation: 4,
    gap: spacing.xs + 2,
    margin: spacing.md,
    padding: spacing.md,
    shadowColor: colors.basalt,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.12,
    shadowRadius: 10,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  orderBadge: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    height: 22,
    justifyContent: 'center',
    width: 22,
  },
  orderText: {
    color: colors.surface,
    fontSize: typography.micro.fontSize - 1,
    fontWeight: '700',
  },
  placeName: {
    color: colors.basalt,
    flex: 1,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  badgeRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  rating: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 2,
  },
  ratingText: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    lineHeight: 18,
  },
  address: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
  },
  moveInfo: {
    color: colors.sea,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  detailButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    flexDirection: 'row',
    gap: 2,
    marginTop: spacing.xs,
  },
  detailText: {
    color: colors.primary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
});
