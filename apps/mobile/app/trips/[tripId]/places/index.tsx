import { useLocalSearchParams } from 'expo-router';

import { PlaceExplorerScreen } from '@/src/features/places/screens/PlaceExplorerScreen';

export default function TripPlaceExplorerRoute() {
  const { tripId, scheduleId } = useLocalSearchParams<{
    tripId: string;
    scheduleId?: string;
  }>();

  return <PlaceExplorerScreen scheduleId={scheduleId} tripId={tripId} />;
}
