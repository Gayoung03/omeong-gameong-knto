import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { getApiErrorMessage } from '@/src/services/apiError';
import { colors } from '@/src/theme';

import { ReviewForm, type ReviewFormValues } from '../components/ReviewForm';
import { useCreateReview } from '../hooks/useCreateReview';

type ReviewCreateScreenProps = {
  placeId: string;
};

export function ReviewCreateScreen({ placeId }: ReviewCreateScreenProps) {
  const router = useRouter();
  const createMutation = useCreateReview();

  const [errorMessage, setErrorMessage] = useState<string>();
  const [isComplete, setIsComplete] = useState(false);

  const handleSubmit = (values: ReviewFormValues) => {
    createMutation.mutate(
      {
        content: values.content,
        localPhotoUris: values.photoUris,
        petPolicyAccurate: values.petPolicyAccurate,
        placeId,
        rating: values.rating,
      },
      {
        // 같은 장소에 30일 안에 다시 쓰면 429 다. 고장이 아니라 규칙이라
        // 서버 규약을 그대로 옮긴 안내 문구를 보여준다.
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
      <ScreenHeader title="리뷰 작성" />
      <ReviewForm
        completeDescription="다른 여행자들에게 도움이 될 거예요."
        completeTitle="리뷰가 등록되었어요"
        discardDescription="작성한 리뷰 내용이 저장되지 않아요."
        errorMessage={errorMessage}
        isComplete={isComplete}
        isSaving={createMutation.isPending}
        onCompleteConfirm={() => {
          setIsComplete(false);
          router.back();
        }}
        onSubmit={handleSubmit}
        savingLabel="등록 중..."
        submitLabel="리뷰 등록"
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});
