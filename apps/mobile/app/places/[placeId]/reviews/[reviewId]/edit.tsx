import { useLocalSearchParams } from 'expo-router';

import { ReviewEditScreen } from '@/src/features/reviews/screens/ReviewEditScreen';

export default function ReviewEditRoute() {
  const { placeId, reviewId } = useLocalSearchParams<{ placeId: string; reviewId: string }>();

  return <ReviewEditScreen placeId={placeId ?? ''} reviewId={reviewId ?? ''} />;
}
