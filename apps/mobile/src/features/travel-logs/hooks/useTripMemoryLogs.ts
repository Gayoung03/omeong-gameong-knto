import { useQueries } from '@tanstack/react-query';

import type { TravelLog, Trip } from '@/src/types/travelLog';

import { getTripHeader, getTripLogs } from '../api/travelLogsApi';

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

  return {
    trip: tripQuery.data,
    logs: logsQuery.data,
    isPending: tripQuery.isPending || logsQuery.isPending,
    isError: tripQuery.isError || logsQuery.isError,
    refetch: () => {
      tripQuery.refetch();
      logsQuery.refetch();
    },
  };
}
