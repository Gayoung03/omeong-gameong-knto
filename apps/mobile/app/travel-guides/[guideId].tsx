import { useLocalSearchParams } from 'expo-router';

import { TravelGuideDetailScreen } from '@/src/features/travel-guides/screens/TravelGuideDetailScreen';

export default function TravelGuideDetailRoute() {
  const { guideId } = useLocalSearchParams<{ guideId: string }>();

  return <TravelGuideDetailScreen guideId={guideId ?? ''} />;
}
