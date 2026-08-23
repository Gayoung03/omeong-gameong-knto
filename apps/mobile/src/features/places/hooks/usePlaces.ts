import { useQuery } from '@tanstack/react-query';

import { getPlaces } from '../api/placesApi';

export const placesQueryKey = ['places', 'list'] as const;

/** 공식 장소 목록. 지역·분류·검색어 필터는 화면에서 건다. */
export function usePlaces() {
  return useQuery({
    queryFn: getPlaces,
    queryKey: placesQueryKey,
  });
}
