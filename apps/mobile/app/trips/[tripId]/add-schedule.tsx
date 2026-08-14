import { useLocalSearchParams } from 'expo-router';

import { AddScheduleScreen } from '@/src/features/trips/screens/AddScheduleScreen';

export default function AddScheduleRoute() {
  const { tripId, scheduleId } = useLocalSearchParams<{ tripId: string; scheduleId?: string }>();

  return <AddScheduleScreen scheduleId={scheduleId} tripId={tripId} />;
}
