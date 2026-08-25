import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { Avatar } from '@/src/components/ui/Avatar';
import { colors, radius, spacing, typography } from '@/src/theme';

import { StarRating } from './StarRating';
import type { Review } from '../types/review';

function formatReviewDate(createdAt: string): string {
  const date = new Date(createdAt);
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
}

type ReviewCardProps = {
  review: Review;
  /** 내 리뷰일 때만 아래에 수정·삭제 줄이 붙는다. 둘 다 없으면 읽기 전용 카드다. */
  onEdit?: (review: Review) => void;
  onDelete?: (review: Review) => void;
};

export function ReviewCard({ review, onEdit, onDelete }: ReviewCardProps) {
  // 남의 리뷰에 메뉴가 보이면 안 된다. 서버가 내려준 isMine 이 유일한 판단 근거다.
  const showOwnerActions = review.isMine && Boolean(onEdit || onDelete);

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Avatar size={32} uri={review.authorAvatar} />
        <View style={styles.headerText}>
          <Text style={styles.authorName}>{review.authorName}</Text>
          <Text style={styles.date}>
            {formatReviewDate(review.createdAt)}
            {review.isEdited && ' · 수정됨'}
            {review.petName && ` · ${review.petName}와 함께`}
          </Text>
        </View>
        <StarRating rating={review.rating} size={13} />
      </View>

      {/* 서버는 별점만 있는 리뷰도 받는다. 내용이 없으면 빈 줄을 만들지 않는다. */}
      {review.content.length > 0 && <Text style={styles.content}>{review.content}</Text>}

      {review.photoUrls.length > 0 && (
        <View style={styles.photoRow}>
          {review.photoUrls.map((uri) => (
            <Image key={uri} source={{ uri }} style={styles.photo} />
          ))}
        </View>
      )}

      {review.petPolicyAccurate !== null && (
        <View
          style={[
            styles.accuracyBadge,
            review.petPolicyAccurate ? styles.accuracyBadgeTrue : styles.accuracyBadgeFalse,
          ]}
        >
          <Text
            style={[
              styles.accuracyText,
              review.petPolicyAccurate ? styles.accuracyTextTrue : styles.accuracyTextFalse,
            ]}
          >
            {review.petPolicyAccurate
              ? '동반정책 정보가 정확했어요'
              : '동반정책 정보가 실제와 달랐어요'}
          </Text>
        </View>
      )}

      {showOwnerActions && (
        // 되돌릴 수 없는 삭제라 시각적 무게를 낮춘다. 작은 회색 글씨 한 줄.
        <View style={styles.ownerActions}>
          {onEdit && (
            <Pressable
              accessibilityRole="button"
              hitSlop={8}
              onPress={() => onEdit(review)}
              style={({ pressed }) => pressed && styles.pressed}
            >
              <Text style={styles.ownerActionText}>수정</Text>
            </Pressable>
          )}
          {onEdit && onDelete && <View style={styles.ownerActionDivider} />}
          {onDelete && (
            <Pressable
              accessibilityRole="button"
              hitSlop={8}
              onPress={() => onDelete(review)}
              style={({ pressed }) => pressed && styles.pressed}
            >
              <Text style={styles.ownerActionText}>삭제</Text>
            </Pressable>
          )}
        </View>
      )}
    </View>
  );
}

const PHOTO_SIZE = 72;

const styles = StyleSheet.create({
  accuracyBadge: {
    alignSelf: 'flex-start',
    borderRadius: radius.full,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs / 2,
  },
  accuracyBadgeFalse: {
    backgroundColor: colors.primarySoft,
  },
  accuracyBadgeTrue: {
    backgroundColor: colors.leafSoft,
  },
  accuracyText: {
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  accuracyTextFalse: {
    color: colors.primary,
  },
  accuracyTextTrue: {
    color: colors.seaDeep,
  },
  authorName: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  card: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    paddingVertical: spacing.md,
  },
  content: {
    color: colors.textStrong,
    fontSize: typography.body.fontSize - 1,
    lineHeight: 20,
    marginTop: spacing.sm,
  },
  date: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  headerText: {
    flex: 1,
  },
  ownerActionDivider: {
    backgroundColor: colors.divider,
    height: 10,
    width: 1,
  },
  ownerActionText: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  ownerActions: {
    alignItems: 'center',
    alignSelf: 'flex-end',
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  photo: {
    borderRadius: radius.md,
    height: PHOTO_SIZE,
    width: PHOTO_SIZE,
  },
  photoRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  pressed: {
    opacity: 0.6,
  },
});
