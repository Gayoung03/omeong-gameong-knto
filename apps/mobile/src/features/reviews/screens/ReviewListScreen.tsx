import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ErrorState } from '@/src/components/feedback/ErrorState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { getApiErrorMessage } from '@/src/services/apiError';
import { colors, radius, spacing, typography } from '@/src/theme';

import { ReviewCard } from '../components/ReviewCard';
import { ReviewDeleteConfirmModal } from '../components/ReviewDeleteConfirmModal';
import { ReviewSummaryHeader } from '../components/ReviewSummaryHeader';
import { useDeleteReview } from '../hooks/useDeleteReview';
import { useReviews } from '../hooks/useReviews';
import type { Review } from '../types/review';

type ReviewListScreenProps = {
  placeId: string;
};

export function ReviewListScreen({ placeId }: ReviewListScreenProps) {
  const router = useRouter();
  const { data, isPending, isError, refetch } = useReviews(placeId);
  const deleteMutation = useDeleteReview();

  const [pendingDelete, setPendingDelete] = useState<Review | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>();

  const goToWrite = () => {
    router.push({ pathname: '/places/[placeId]/reviews/new', params: { placeId } });
  };

  const goToEdit = (review: Review) => {
    router.push({
      params: { placeId, reviewId: review.id },
      pathname: '/places/[placeId]/reviews/[reviewId]/edit',
    });
  };

  const confirmDelete = () => {
    if (!pendingDelete) return;

    deleteMutation.mutate(
      { placeId, reviewId: pendingDelete.id },
      {
        onError: (error) => {
          setPendingDelete(null);
          setErrorMessage(getApiErrorMessage(error).description);
        },
        onSuccess: () => {
          setPendingDelete(null);
          setErrorMessage(undefined);
        },
      },
    );
  };

  const renderBody = () => {
    if (isError) return <ErrorState onRetry={() => refetch()} />;

    if (!data || data.summary.totalCount === 0) {
      return (
        <EmptyState
          actionLabel="리뷰 쓰기"
          description="이 장소를 다녀왔다면 첫 리뷰를 남겨보세요."
          icon="star-outline"
          onPressAction={goToWrite}
          title="아직 리뷰가 없어요"
        />
      );
    }

    return (
      <FlatList
        ListHeaderComponent={<ReviewSummaryHeader summary={data.summary} />}
        contentContainerStyle={styles.listContent}
        data={data.items}
        keyExtractor={(review) => review.id}
        renderItem={({ item }) => (
          <ReviewCard onDelete={setPendingDelete} onEdit={goToEdit} review={item} />
        )}
      />
    );
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="리뷰" />

      {isPending ? (
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : (
        renderBody()
      )}

      {errorMessage && <Text style={styles.mutationError}>{errorMessage}</Text>}

      <Pressable onPress={goToWrite} style={styles.writeButton}>
        <Text style={styles.writeButtonText}>리뷰 쓰기</Text>
      </Pressable>

      <ReviewDeleteConfirmModal
        isDeleting={deleteMutation.isPending}
        onCancel={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        visible={pendingDelete !== null}
      />
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
    gap: spacing.xs,
    paddingBottom: 96,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  mutationError: {
    color: colors.error,
    fontSize: typography.label.fontSize,
    paddingBottom: spacing.sm,
    paddingHorizontal: spacing.lg,
    textAlign: 'center',
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  writeButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    bottom: spacing.lg,
    left: spacing.lg,
    paddingVertical: spacing.sm + 2,
    position: 'absolute',
    right: spacing.lg,
  },
  writeButtonText: {
    color: colors.surface,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
});
