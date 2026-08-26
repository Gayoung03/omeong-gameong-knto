import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import { useReviews } from '../hooks/useReviews';
import { ReviewCard } from './ReviewCard';

const PREVIEW_COUNT = 2;

/** 장소 상세 화면에 넣는 리뷰 요약. 전체 목록·작성은 별도 화면에서 한다. */
export function ReviewPreviewSection({ placeId }: { placeId: string }) {
  const router = useRouter();
  const { data } = useReviews(placeId);

  const goToList = () => {
    router.push({ pathname: '/places/[placeId]/reviews', params: { placeId } });
  };
  const goToWrite = () => {
    router.push({ pathname: '/places/[placeId]/reviews/new', params: { placeId } });
  };

  // 개수는 반드시 summary 를 쓴다. items 는 20건씩 끊어 오는 한 페이지라
  // 리뷰가 21개 넘는 장소에서 길이로 세면 20에서 멈춘다.
  const totalCount = data?.summary.totalCount ?? 0;
  const previewReviews = (data?.items ?? []).slice(0, PREVIEW_COUNT);

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.cardLabel}>리뷰 {totalCount}개</Text>
        <Pressable accessibilityRole="button" onPress={goToWrite}>
          <Text style={styles.writeLink}>리뷰 쓰기</Text>
        </Pressable>
      </View>

      {previewReviews.length === 0 ? (
        <Text style={styles.emptyText}>아직 리뷰가 없어요. 첫 리뷰를 남겨보세요.</Text>
      ) : (
        <>
          {previewReviews.map((review) => (
            <ReviewCard key={review.id} review={review} />
          ))}
          <Pressable accessibilityRole="button" onPress={goToList} style={styles.viewAllButton}>
            <Text style={styles.viewAllText}>리뷰 전체보기</Text>
          </Pressable>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
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
  emptyText: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
  },
  headerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  viewAllButton: {
    alignItems: 'center',
    paddingTop: spacing.xs,
  },
  viewAllText: {
    color: colors.primary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  writeLink: {
    color: colors.primary,
    fontSize: typography.body.fontSize - 3,
    fontWeight: '600',
  },
});
