import { useLocalSearchParams } from 'expo-router';

import { ReviewCreateScreen } from '@/src/features/reviews/screens/ReviewCreateScreen';

export default function ReviewCreateRoute() {
  const { placeId } = useLocalSearchParams<{ placeId: string }>();

  return <ReviewCreateScreen placeId={placeId ?? ''} />;
}
