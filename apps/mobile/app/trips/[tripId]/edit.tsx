import { useLocalSearchParams } from 'expo-router';

import { TripScheduleEditScreen } from '@/src/features/trips/screens/TripScheduleEditScreen';

export default function TripEditRoute() {
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  return <TripScheduleEditScreen tripId={tripId} />;
}
