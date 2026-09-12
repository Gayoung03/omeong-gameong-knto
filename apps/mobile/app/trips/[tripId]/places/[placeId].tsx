import { useLocalSearchParams } from 'expo-router';

import { PlaceDetailScreen } from '@/src/features/places/screens/PlaceDetailScreen';

export default function TripPlaceDetailRoute() {
  const { placeId, tripId, scheduleId } = useLocalSearchParams<{
    placeId: string;
    tripId: string;
    scheduleId?: string;
  }>();

  return <PlaceDetailScreen placeId={placeId} scheduleId={scheduleId} tripId={tripId} />;
}
