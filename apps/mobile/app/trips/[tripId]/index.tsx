import { useLocalSearchParams } from 'expo-router';

import { TripDetailScreen } from '@/src/features/trips/screens/TripDetailScreen';

export default function TripDetailRoute() {
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  return <TripDetailScreen tripId={tripId ?? ''} />;
}
