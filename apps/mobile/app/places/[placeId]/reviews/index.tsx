import { useLocalSearchParams } from 'expo-router';

import { ReviewListScreen } from '@/src/features/reviews/screens/ReviewListScreen';

export default function ReviewListRoute() {
  const { placeId } = useLocalSearchParams<{ placeId: string }>();

  return <ReviewListScreen placeId={placeId ?? ''} />;
}
