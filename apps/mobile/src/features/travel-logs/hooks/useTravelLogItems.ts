import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';

import type { TravelLogListItem } from '@/src/types/travelLog';

import { getTravelLogGroups } from '../api/travelLogsApi';
import { useSavedLogStore } from '../stores/useSavedLogStore';

export const travelLogQueryKey = ['travel-logs'] as const;

export function useTravelLogItems() {
  const savedLogs = useSavedLogStore((state) => state.savedLogs);
  const query = useQuery<TravelLogListItem[]>({
    queryKey: travelLogQueryKey,
    queryFn: getTravelLogGroups,
  });
  const data = useMemo(() => {
    if (!query.data || savedLogs.length === 0) return query.data;

    return query.data.map((item) => {
      if (item.kind === 'trip') {
        const additions = savedLogs.filter((log) => log.tripId === item.trip.tripId);
        if (additions.length === 0) return item;
        return {
          kind: 'trip' as const,
          trip: {
            ...item.trip,
            logCount: item.trip.logCount + additions.length,
            previewLogs: [...additions, ...item.trip.previewLogs].slice(0, 4),
          },
        };
      }

      const additions = savedLogs.filter((log) => log.tripId === null);
      if (additions.length === 0) return item;
      return {
        kind: 'ungrouped' as const,
        group: {
          ...item.group,
          logCount: item.group.logCount + additions.length,
          previewLogs: [...additions, ...item.group.previewLogs].slice(0, 4),
        },
      };
    });
  }, [query.data, savedLogs]);

  return { ...query, data };
}
