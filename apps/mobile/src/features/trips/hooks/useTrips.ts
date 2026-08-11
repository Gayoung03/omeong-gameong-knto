import { useQuery } from '@tanstack/react-query';

import { getLatestTrip, getTrip, getTrips } from '../api/tripsApi';

export const tripQueryKeys = {
  all: ['trips'] as const,
  list: () => [...tripQueryKeys.all, 'list'] as const,
  detail: (tripId: string) => [...tripQueryKeys.all, 'detail', tripId] as const,
  latest: () => [...tripQueryKeys.all, 'latest'] as const,
};

/** 내 여행 목록 */
export function useTrips() {
  return useQuery({
    queryKey: tripQueryKeys.list(),
    queryFn: getTrips,
  });
}

/** 여행 상세 */
export function useTrip(tripId: string | undefined) {
  return useQuery({
    queryKey: tripQueryKeys.detail(tripId ?? ''),
    queryFn: () => getTrip(tripId as string),
    enabled: Boolean(tripId),
  });
}

/** 가장 최근 여행 (내 여행 탭 진입 시 기본 표시용) */
export function useLatestTrip() {
  return useQuery({
    queryKey: tripQueryKeys.latest(),
    queryFn: getLatestTrip,
  });
}
