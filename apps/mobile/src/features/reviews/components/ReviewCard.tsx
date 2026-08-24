import { Image, StyleSheet, Text, View } from 'react-native';

import { Avatar } from '@/src/components/ui/Avatar';
import { colors, radius, spacing, typography } from '@/src/theme';

import type { Review } from '../types/review';
import { StarRating } from './StarRating';

function formatReviewDate(createdAt: string): string {
  const date = new Date(createdAt);
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
}

export function ReviewCard({ review }: { review: Review }) {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Avatar size={32} uri={review.authorAvatar} />
        <View style={styles.headerText}>
          <Text style={styles.authorName}>{review.authorName}</Text>
          <Text style={styles.date}>{formatReviewDate(review.createdAt)}</Text>
        </View>
        <StarRating rating={review.rating} size={13} />
      </View>

      <Text style={styles.content}>{review.content}</Text>

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
});
