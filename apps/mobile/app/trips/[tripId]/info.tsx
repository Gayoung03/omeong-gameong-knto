import { useLocalSearchParams } from 'expo-router';

import { TripInfoScreen } from '@/src/features/trips/screens/TripInfoScreen';

export default function TripInfoRoute() {
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  return <TripInfoScreen tripId={tripId} />;
}
