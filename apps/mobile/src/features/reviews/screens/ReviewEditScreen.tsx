import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorState } from '@/src/components/feedback/ErrorState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { getApiErrorMessage } from '@/src/services/apiError';
import { colors } from '@/src/theme';

import { ReviewForm, type ReviewFormValues } from '../components/ReviewForm';
import { useReviews } from '../hooks/useReviews';
import { useUpdateReview } from '../hooks/useUpdateReview';
import type { Review } from '../types/review';

type ReviewEditScreenProps = {
  placeId: string;
  reviewId: string;
};

/**
 * 리뷰 수정.
 *
 * **리뷰 한 건만 가져오는 엔드포인트가 없다.** 서버에 있는 것은 장소별 목록뿐이라
 * 그 목록에서 찾아 쓴다. 그래서 목록에 없는 리뷰(21번째 이후)는 이 화면이 못 연다 —
 * 지금은 목록 화면에서만 들어오므로 실제로 걸리지 않지만, 페이지를 붙이면 함께 손봐야 한다.
 */
export function ReviewEditScreen({ placeId, reviewId }: ReviewEditScreenProps) {
  const router = useRouter();
  const { data, isPending, isError, refetch } = useReviews(placeId);

  if (isPending) {
    return (
      <SafeAreaView edges={['top']} style={styles.safeArea}>
        <ScreenHeader title="리뷰 수정" />
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  const review = data?.items.find((item) => item.id === reviewId);

  if (isError || !review) {
    return (
      <SafeAreaView edges={['top']} style={styles.safeArea}>
        <ScreenHeader title="리뷰 수정" />
        <ErrorState
          description={isError ? undefined : '삭제되었거나 더 이상 볼 수 없는 리뷰예요.'}
          onRetry={() => refetch()}
          title={isError ? undefined : '리뷰를 찾을 수 없어요'}
        />
      </SafeAreaView>
    );
  }

  // 초기값이 정해진 뒤에 폼을 만든다. useEffect 로 나중에 채우면
  // react-hooks/set-state-in-effect 에 걸리고, 첫 프레임이 빈 폼으로 깜빡인다.
  return <ReviewEditForm placeId={placeId} review={review} onDone={() => router.back()} />;
}

type ReviewEditFormProps = {
  placeId: string;
  review: Review;
  onDone: () => void;
};

function ReviewEditForm({ placeId, review, onDone }: ReviewEditFormProps) {
  const updateMutation = useUpdateReview();

  const [errorMessage, setErrorMessage] = useState<string>();
  const [isComplete, setIsComplete] = useState(false);

  const handleSubmit = (values: ReviewFormValues) => {
    updateMutation.mutate(
      {
        content: values.content,
        petPolicyAccurate: values.petPolicyAccurate,
        photoUris: values.photoUris,
        placeId,
        rating: values.rating,
        reviewId: review.id,
      },
      {
        onError: (error) => setErrorMessage(getApiErrorMessage(error).description),
        onSuccess: () => {
          setErrorMessage(undefined);
          setIsComplete(true);
        },
      },
    );
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="리뷰 수정" />
      <ReviewForm
        completeDescription="바뀐 내용이 리뷰에 반영됐어요."
        completeTitle="리뷰가 수정되었어요"
        discardDescription="수정한 내용이 저장되지 않아요."
        errorMessage={errorMessage}
        initialValues={{
          content: review.content,
          petPolicyAccurate: review.petPolicyAccurate,
          photoUris: review.photoUrls,
          rating: review.rating,
        }}
        isComplete={isComplete}
        isSaving={updateMutation.isPending}
        onCompleteConfirm={() => {
          setIsComplete(false);
          onDone();
        }}
        onSubmit={handleSubmit}
        savingLabel="저장 중..."
        submitLabel="수정 완료"
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
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});
