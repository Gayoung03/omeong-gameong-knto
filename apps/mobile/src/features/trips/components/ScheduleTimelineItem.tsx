import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

import { placeThumbnails } from '../constants/placeThumbnail';
import type { ScheduleItem, TransportType } from '../types/trip';
import { formatMoveInfo, getPlaceCategoryLabel } from '../utils/tripFormat';
import { PetPolicyBadge } from './PetPolicyBadge';

const TRANSPORT_ICONS: Record<TransportType, 'boat-outline' | 'car-outline' | 'walk-outline'> = {
  car: 'car-outline',
  ferry: 'boat-outline',
  walk: 'walk-outline',
};

type ScheduleTimelineItemProps = {
  item: ScheduleItem;
  isFirst: boolean;
  isLast: boolean;
  /**
   * 이 장소를 저장했는지.
   *
   * `item.isSaved` 를 쓰지 않는다 — 저장 목록은 여행 응답이 아니라
   * `features/saved` 가 들고 있어서 어댑터가 알 수 없다(늘 false 로 온다).
   */
  isSaved: boolean;
  onPressItem: (placeId: string) => void;
  /** 저장은 **장소** 단위다. 같은 장소를 여러 날에 담아도 하나로 취급한다. */
  onToggleSave: (placeId: string, isSaved: boolean) => void;
};

/**
 * 일정 카드.
 *
 * 루트 추천 결과 화면의 가로형 카드와 형태를 맞췄다.
 * 왼쪽 순번 배지 · 썸네일 · 본문 · 오른쪽 저장 버튼 순이고,
 * 시각은 추천 결과 카드처럼 본문 최상단에 강조해 표시한다.
 */
export function ScheduleTimelineItem({
  isFirst,
  isLast,
  item,
  isSaved,
  onPressItem,
  onToggleSave,
}: ScheduleTimelineItemProps) {
  const thumbnail = placeThumbnails[item.place.category];

  return (
    <View style={styles.timelineItem}>
      <View style={styles.railColumn}>
        {!isFirst ? <View style={styles.railTop} /> : null}
        {!isLast ? <View style={styles.railBottom} /> : null}
        <View style={styles.orderBadge}>
          <Text style={styles.orderText}>{item.order}</Text>
        </View>
      </View>

      <View style={styles.itemContent}>
        <View style={styles.cardWrapper}>
          <Pressable
            accessibilityRole="button"
            onPress={item.place.isCustom ? undefined : () => onPressItem(item.place.id)}
            style={({ pressed }) => [styles.card, pressed && styles.pressed]}
          >
            {item.place.imageUrl ? (
              <RemoteImage
                borderRadius={radius.md}
                style={styles.thumbnail}
                uri={item.place.imageUrl}
              />
            ) : (
              <View
                style={[
                  styles.thumbnail,
                  styles.thumbnailFallback,
                  { backgroundColor: thumbnail.background },
                ]}
              >
                <Text style={styles.thumbnailEmoji}>{thumbnail.emoji}</Text>
              </View>
            )}

            <View style={styles.content}>
              <Text style={styles.timeText}>{item.startTime ?? '시간 미정'}</Text>
              <View style={styles.titleRow}>
                <Text numberOfLines={1} style={styles.placeName}>
                  {item.place.name}
                </Text>
                <View style={styles.categoryBadge}>
                  <Text style={styles.categoryText}>
                    {getPlaceCategoryLabel(item.place.category)}
                  </Text>
                </View>
              </View>

              <Text numberOfLines={2} style={styles.description}>
                {item.place.description}
              </Text>

              <PetPolicyBadge petPolicy={item.place.petPolicy} />

              {item.memo.length > 0 ? (
                <View style={styles.memoRow}>
                  <Ionicons color={colors.textTertiary} name="create-outline" size={12} />
                  <Text numberOfLines={2} style={styles.memo}>
                    {item.memo}
                  </Text>
                </View>
              ) : null}
            </View>

            {/* 저장 버튼이 앉을 자리. 실제 버튼은 카드 Pressable 바깥에 있다 */}
            <View style={styles.saveSlot} />
          </Pressable>

          {/*
          웹에서 <button> 안에 <button> 이 들어가면 안 되므로 카드 Pressable 의
          자식이 아니라 형제로 두고, 원래 자리에 겹쳐 놓는다.
        */}
          {!item.place.isCustom ? (
            <Pressable
              accessibilityLabel={isSaved ? '저장 해제' : '저장'}
              accessibilityRole="button"
              onPress={() => onToggleSave(item.place.id, isSaved)}
              style={styles.saveButton}
            >
              {/* 장소 탐색 화면과 같은 하트 아이콘·색을 쓴다. */}
              <Ionicons
                color={isSaved ? colors.primary : colors.textSecondary}
                name={isSaved ? 'heart' : 'heart-outline'}
                size={16}
              />
            </Pressable>
          ) : null}
        </View>

        {!isLast ? (
          <View style={styles.travelRow}>
            {item.moveToNext ? (
              <>
                <Ionicons
                  color={colors.textTertiary}
                  name={TRANSPORT_ICONS[item.moveToNext.transport]}
                  size={13}
                />
                <Text style={styles.travelText}>
                  {formatMoveInfo(
                    item.moveToNext.transport,
                    item.moveToNext.distanceMeters,
                    item.moveToNext.durationMinutes,
                  )}
                </Text>
              </>
            ) : null}
          </View>
        ) : null}
      </View>
    </View>
  );
}

const THUMBNAIL_SIZE = 72;

const styles = StyleSheet.create({
  card: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg - 1,
    borderWidth: 1,
    flexDirection: 'row',
    minHeight: 100,
    padding: spacing.sm + 2,
    shadowColor: colors.basalt,
    shadowOffset: { height: 2, width: 0 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
  },
  cardWrapper: {
    position: 'relative',
  },
  categoryBadge: {
    backgroundColor: colors.neutralGray,
    borderRadius: radius.sm - 3,
    paddingHorizontal: spacing.xs + 1,
    paddingVertical: 2,
  },
  categoryText: {
    color: colors.textSecondary,
    fontSize: 9,
    fontWeight: '700',
  },
  content: {
    flex: 1,
    gap: spacing.xs + 1,
    paddingHorizontal: spacing.sm + 2,
  },
  itemContent: {
    flex: 1,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    fontWeight: '400',
    lineHeight: 15,
  },
  memo: {
    color: colors.textTertiary,
    flex: 1,
    fontSize: typography.micro.fontSize,
    lineHeight: 15,
  },
  memoRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.xs,
  },
  orderBadge: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    height: 24,
    justifyContent: 'center',
    marginLeft: 8,
    marginTop: 12,
    width: 24,
    zIndex: 1,
  },
  orderText: {
    color: colors.surface,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
  placeName: {
    color: colors.basalt,
    flexShrink: 1,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '800',
  },
  pressed: {
    opacity: 0.85,
  },
  railBottom: {
    backgroundColor: overlayColors.primaryBorder,
    bottom: 0,
    left: 19,
    position: 'absolute',
    top: 24,
    width: 2,
  },
  railColumn: {
    position: 'relative',
    width: 40,
  },
  railTop: {
    backgroundColor: overlayColors.primaryBorder,
    height: 24,
    left: 19,
    position: 'absolute',
    top: 0,
    width: 2,
  },
  saveButton: {
    padding: spacing.sm,
    position: 'absolute',
    right: spacing.xs,
    top: spacing.xs,
  },
  saveSlot: {
    height: 16,
    width: 16,
  },
  thumbnail: {
    height: THUMBNAIL_SIZE,
    width: THUMBNAIL_SIZE,
  },
  thumbnailEmoji: {
    fontSize: 30,
  },
  thumbnailFallback: {
    alignItems: 'center',
    borderRadius: radius.md,
    justifyContent: 'center',
  },
  timeText: {
    color: colors.primary,
    fontSize: typography.caption.fontSize,
    fontWeight: '800',
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs + 2,
  },
  travelRow: {
    alignItems: 'center',
    flexDirection: 'row',
    height: 34,
    paddingLeft: spacing.sm + 2,
  },
  travelText: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize - 1,
    marginLeft: spacing.xs,
  },
  timelineItem: {
    flexDirection: 'row',
  },
});
