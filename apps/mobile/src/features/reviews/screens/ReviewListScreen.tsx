import { useRouter } from 'expo-router';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ErrorState } from '@/src/components/feedback/ErrorState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, radius, spacing, typography } from '@/src/theme';

import { ReviewCard } from '../components/ReviewCard';
import { useReviews } from '../hooks/useReviews';

type ReviewListScreenProps = {
  placeId: string;
};

export function ReviewListScreen({ placeId }: ReviewListScreenProps) {
  const router = useRouter();
  const { data: reviews, isPending, isError, refetch } = useReviews(placeId);

  const goToWrite = () => {
    router.push({ pathname: '/places/[placeId]/reviews/new', params: { placeId } });
  };

  const renderBody = () => {
    if (isPending) return null;

    if (isError) return <ErrorState onRetry={() => refetch()} />;

    if (!reviews || reviews.length === 0) {
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
        contentContainerStyle={styles.listContent}
        data={reviews}
        keyExtractor={(review) => review.id}
        renderItem={({ item }) => <ReviewCard review={item} />}
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

      <Pressable onPress={goToWrite} style={styles.writeButton}>
        <Text style={styles.writeButtonText}>리뷰 쓰기</Text>
      </Pressable>
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
    paddingBottom: 96,
    paddingHorizontal: spacing.lg,
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
