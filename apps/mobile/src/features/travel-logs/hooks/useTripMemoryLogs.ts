import { useQueries } from '@tanstack/react-query';
import { useMemo } from 'react';

import type { TravelLog, Trip } from '@/src/types/travelLog';

import { getTripHeader, getTripLogs } from '../api/travelLogsApi';
import { useSavedLogStore } from '../stores/useSavedLogStore';

export function tripDetailQueryKey(tripId: string) {
  return ['travel-logs', 'trip', tripId] as const;
}

export function tripLogsQueryKey(tripId: string) {
  return ['travel-logs', 'trip', tripId, 'logs'] as const;
}

type TripMemoryQueryResult = {
  trip: Trip | null | undefined;
  logs: TravelLog[] | undefined;
  isPending: boolean;
  isError: boolean;
  refetch: () => void;
};

/** 여행 모아보기 헤더(제목·기간·기록 수)와 날짜별 로그 목록을 함께 불러온다. */
export function useTripMemoryLogs(tripId: string): TripMemoryQueryResult {
  const savedLogs = useSavedLogStore((state) => state.savedLogs);
  const [tripQuery, logsQuery] = useQueries({
    queries: [
      {
        queryKey: tripDetailQueryKey(tripId),
        queryFn: () => getTripHeader(tripId),
      },
      {
        queryKey: tripLogsQueryKey(tripId),
        queryFn: () => getTripLogs(tripId),
      },
    ],
  });
  const additions = useMemo(
    () => savedLogs.filter((log) => log.tripId === tripId),
    [savedLogs, tripId],
  );
  const trip = useMemo(
    () =>
      tripQuery.data && additions.length > 0
        ? { ...tripQuery.data, logCount: tripQuery.data.logCount + additions.length }
        : tripQuery.data,
    [additions, tripQuery.data],
  );
  const logs = useMemo(
    () => (logsQuery.data ? [...additions, ...logsQuery.data] : logsQuery.data),
    [additions, logsQuery.data],
  );

  return {
    trip,
    logs,
    isPending: tripQuery.isPending || logsQuery.isPending,
    isError: tripQuery.isError || logsQuery.isError,
    refetch: () => {
      tripQuery.refetch();
      logsQuery.refetch();
    },
  };
}
