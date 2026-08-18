import { useLocalSearchParams } from 'expo-router';

import { PlaceDetailScreen } from '@/src/features/places/screens/PlaceDetailScreen';

export default function PlaceDetailRoute() {
  const { placeId } = useLocalSearchParams<{ placeId: string }>();

  return <PlaceDetailScreen placeId={placeId ?? ''} />;
}
