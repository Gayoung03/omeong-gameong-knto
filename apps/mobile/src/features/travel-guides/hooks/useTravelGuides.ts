import { useQuery } from '@tanstack/react-query';

import { getTravelGuideDetail, getTravelGuideOverview } from '../api/guidesApi';

export const travelGuideOverviewQueryKey = ['travel-guides', 'overview'] as const;

export function travelGuideDetailQueryKey(guideId: string) {
  return ['travel-guides', 'detail', guideId] as const;
}

export function useTravelGuideOverview() {
  return useQuery({
    queryFn: getTravelGuideOverview,
    queryKey: travelGuideOverviewQueryKey,
  });
}

export function useTravelGuideDetail(guideId: string) {
  return useQuery({
    enabled: guideId.length > 0,
    queryFn: () => getTravelGuideDetail(guideId),
    queryKey: travelGuideDetailQueryKey(guideId),
  });
}
