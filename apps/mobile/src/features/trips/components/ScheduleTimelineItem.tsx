import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

import { placeThumbnails } from '../constants/placeThumbnail';
import type { ScheduleItem, TransportType } from '../types/trip';
import { formatMoveInfo, formatTimeLabel, getPlaceCategoryLabel } from '../utils/tripFormat';
import { PetPolicyBadge } from './PetPolicyBadge';

const TRANSPORT_ICONS: Record<TransportType, 'boat-outline' | 'car-outline' | 'walk-outline'> = {
  car: 'car-outline',
  ferry: 'boat-outline',
  walk: 'walk-outline',
};

type ScheduleTimelineItemProps = {
  item: ScheduleItem;
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
 * 왼쪽 열(순번 + 시각) · 썸네일 · 본문 · 오른쪽 저장 버튼 순이고,
 * 순번 배지는 화면 전체에서 키 컬러(`colors.primary`) 하나로 통일한다.
 */
export function ScheduleTimelineItem({
  isLast,
  item,
  isSaved,
  onPressItem,
  onToggleSave,
}: ScheduleTimelineItemProps) {
  const thumbnail = placeThumbnails[item.place.category];

  return (
    <View>
      <View style={styles.cardWrapper}>
        <Pressable
          accessibilityRole="button"
          onPress={() => onPressItem(item.place.id)}
          style={({ pressed }) => [styles.card, pressed && styles.pressed]}
        >
          <View style={styles.timelineColumn}>
            <View style={styles.orderBadge}>
              <Text style={styles.orderText}>{item.order}</Text>
            </View>
            {item.startTime ? (
              <Text style={styles.timeText}>{formatTimeLabel(item.startTime)}</Text>
            ) : null}
          </View>

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
      </View>

      {!isLast && item.moveToNext ? (
        <View style={styles.travelRow}>
          <View style={styles.travelLine} />
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
        </View>
      ) : null}
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
    width: 24,
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
    color: colors.basalt,
    fontSize: typography.micro.fontSize - 1,
    fontWeight: '800',
    marginTop: spacing.xs + 2,
  },
  timelineColumn: {
    alignItems: 'center',
    alignSelf: 'stretch',
    paddingTop: spacing.xs + 2,
    width: 38,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.xs + 2,
  },
  travelLine: {
    backgroundColor: overlayColors.primaryBorder,
    height: 26,
    marginRight: spacing.sm + 2,
    width: 2,
  },
  travelRow: {
    alignItems: 'center',
    flexDirection: 'row',
    height: 26,
    marginLeft: 18,
  },
  travelText: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize - 1,
    marginLeft: spacing.xs,
  },
});
