import { useQuery } from '@tanstack/react-query';

import { getPlaceDetail } from '../api/placesApi';

export function placeDetailQueryKey(placeId: string) {
  return ['places', 'detail', placeId] as const;
}

export function usePlaceDetail(placeId: string) {
  return useQuery({
    enabled: placeId.length > 0,
    queryFn: () => getPlaceDetail(placeId),
    queryKey: placeDetailQueryKey(placeId),
  });
}
