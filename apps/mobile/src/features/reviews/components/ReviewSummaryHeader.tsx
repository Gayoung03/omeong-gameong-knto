import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import { StarRating } from './StarRating';
import { REVIEW_RATING_MAX, REVIEW_RATING_MIN, type ReviewSummary } from '../types/review';

/** 5점부터 1점까지 위에서 아래로 내려가는 순서. */
const RATING_ROWS = Array.from(
  { length: REVIEW_RATING_MAX - REVIEW_RATING_MIN + 1 },
  (_, index) => REVIEW_RATING_MAX - index,
);

/**
 * 장소 하나의 리뷰 집계.
 *
 * 여기 숫자는 전부 서버가 센 값이다. 목록은 20건씩 끊어 오므로
 * 화면이 `items.length` 로 세면 21번째부터 어긋난다.
 */
export function ReviewSummaryHeader({ summary }: { summary: ReviewSummary }) {
  const { averageRating, totalCount, ratingDistribution, petPolicyAccurateRate } = summary;

  return (
    <View style={styles.card}>
      <View style={styles.scoreRow}>
        <View style={styles.scoreGroup}>
          <Text style={styles.score}>
            {averageRating === null ? '-' : averageRating.toFixed(1)}
          </Text>
          <View style={styles.scoreMeta}>
            {/* 평균은 소수점이라 별은 반올림해 그린다. 숫자가 정확한 값이다. */}
            <StarRating rating={Math.round(averageRating ?? 0)} size={14} />
            <Text style={styles.totalCount}>리뷰 {totalCount}개</Text>
          </View>
        </View>

        {petPolicyAccurateRate !== null && (
          <View style={styles.accuracyBox}>
            <Text style={styles.accuracyValue}>{Math.round(petPolicyAccurateRate * 100)}%</Text>
            <Text style={styles.accuracyLabel}>동반정책 일치</Text>
          </View>
        )}
      </View>

      {totalCount > 0 && (
        <View style={styles.distribution}>
          {RATING_ROWS.map((rating) => {
            const count = ratingDistribution[String(rating)] ?? 0;
            const ratio = totalCount === 0 ? 0 : count / totalCount;

            return (
              <View key={rating} style={styles.distributionRow}>
                <Text style={styles.distributionLabel}>{rating}점</Text>
                <View style={styles.track}>
                  <View style={[styles.fill, { width: `${ratio * 100}%` }]} />
                </View>
                <Text style={styles.distributionCount}>{count}</Text>
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  accuracyBox: {
    alignItems: 'center',
    backgroundColor: colors.leafSoft,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  accuracyLabel: {
    color: colors.seaDeep,
    fontSize: typography.micro.fontSize,
    marginTop: spacing.xs / 2,
  },
  accuracyValue: {
    color: colors.seaDeep,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: '700',
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.md,
  },
  distribution: {
    gap: spacing.xs,
  },
  distributionCount: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    minWidth: 24,
    textAlign: 'right',
  },
  distributionLabel: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    minWidth: 26,
  },
  distributionRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  fill: {
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    height: '100%',
  },
  score: {
    color: colors.textPrimary,
    fontSize: 34,
    fontWeight: '700',
  },
  scoreGroup: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.md,
  },
  scoreMeta: {
    gap: spacing.xs,
  },
  scoreRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  totalCount: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
  track: {
    backgroundColor: colors.neutralGray,
    borderRadius: radius.full,
    flex: 1,
    height: 6,
    overflow: 'hidden',
  },
});
