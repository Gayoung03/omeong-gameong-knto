import { useQuery } from '@tanstack/react-query';

import type { TravelLogListItem } from '@/src/types/travelLog';

import { getTravelLogGroups } from '../api/travelLogsApi';

export const travelLogQueryKey = ['travel-logs'] as const;

export function useTravelLogItems() {
  return useQuery<TravelLogListItem[]>({
    queryKey: travelLogQueryKey,
    queryFn: getTravelLogGroups,
  });
}
