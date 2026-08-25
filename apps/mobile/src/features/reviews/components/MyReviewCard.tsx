import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { colors, radius, spacing, typography } from '@/src/theme';

import { StarRating } from './StarRating';
import type { MyReview } from '../types/review';

function formatReviewDate(createdAt: string): string {
  const date = new Date(createdAt);
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`;
}

type MyReviewCardProps = {
  review: MyReview;
  onPress: (review: MyReview) => void;
};

/**
 * 내가 쓴 리뷰 한 건.
 *
 * 장소별 목록의 `ReviewCard` 와 모양이 비슷하지만 응답이 다르다 —
 * 작성자가 빠지고 어느 장소에 썼는지가 들어온다. 그래서 카드를 나눠 뒀다.
 */
export function MyReviewCard({ review, onPress }: MyReviewCardProps) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => onPress(review)}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <View style={styles.header}>
        <RemoteImage
          borderRadius={radius.md}
          style={styles.placeImage}
          uri={review.placeImageUrl ?? undefined}
        />
        <View style={styles.headerText}>
          <Text numberOfLines={1} style={styles.placeName}>
            {review.placeName}
          </Text>
          <View style={styles.metaRow}>
            <StarRating rating={review.rating} size={12} />
            <Text style={styles.date}>{formatReviewDate(review.createdAt)}</Text>
          </View>
        </View>
      </View>

      {review.content.length > 0 && (
        <Text numberOfLines={3} style={styles.content}>
          {review.content}
        </Text>
      )}

      {review.photoUrls.length > 0 && (
        <View style={styles.photoRow}>
          {review.photoUrls.map((uri) => (
            <Image key={uri} source={{ uri }} style={styles.photo} />
          ))}
        </View>
      )}
    </Pressable>
  );
}

const PHOTO_SIZE = 64;
const PLACE_IMAGE_SIZE = 48;

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  content: {
    color: colors.textStrong,
    fontSize: typography.body.fontSize - 1,
    lineHeight: 20,
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
    gap: spacing.xs,
  },
  metaRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  photo: {
    borderRadius: radius.md,
    height: PHOTO_SIZE,
    width: PHOTO_SIZE,
  },
  photoRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  placeImage: {
    height: PLACE_IMAGE_SIZE,
    width: PLACE_IMAGE_SIZE,
  },
  placeName: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: '700',
  },
  pressed: {
    opacity: 0.85,
  },
});
