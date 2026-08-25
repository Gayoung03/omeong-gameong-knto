import { useRouter } from 'expo-router';
import { ActivityIndicator, FlatList, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ErrorState } from '@/src/components/feedback/ErrorState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, spacing } from '@/src/theme';

import { MyReviewCard } from '../components/MyReviewCard';
import { useMyReviews } from '../hooks/useMyReviews';
import type { MyReview } from '../types/review';

/**
 * 내가 쓴 리뷰 목록.
 *
 * 카드를 누르면 리뷰가 아니라 **장소 상세**로 간다. 수정·삭제는 그 장소의
 * 리뷰 목록에서 하도록 한 곳에 모아뒀다 — 같은 동작을 두 화면에 두면
 * 어느 쪽 목록을 새로 받아야 하는지가 갈린다.
 */
export function MyReviewsScreen() {
  const router = useRouter();
  const { data, isPending, isError, refetch } = useMyReviews();

  const openPlace = (review: MyReview) => {
    router.push({ params: { placeId: review.placeId }, pathname: '/places/[placeId]' });
  };

  const renderBody = () => {
    if (isError) return <ErrorState onRetry={() => refetch()} />;

    if (!data || data.items.length === 0) {
      return (
        <EmptyState
          description="다녀온 장소에 리뷰를 남기면 여기 모여요."
          icon="star-outline"
          title="아직 쓴 리뷰가 없어요"
        />
      );
    }

    return (
      <FlatList
        contentContainerStyle={styles.listContent}
        data={data.items}
        keyExtractor={(review) => review.id}
        renderItem={({ item }) => <MyReviewCard onPress={openPlace} review={item} />}
      />
    );
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="내가 쓴 리뷰" />
      {isPending ? (
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : (
        renderBody()
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  centered: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
  },
  listContent: {
    gap: spacing.sm,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});
