import { useInfiniteQuery, type InfiniteData } from '@tanstack/react-query';

import { getPlaces, type PlaceListFilters, type PlacePage } from '../api/placesApi';

export const placesQueryKey = ['places', 'list'] as const;

/** 공식 장소 목록. 필터가 바뀌면 queryKey가 바뀌어 첫 페이지부터 다시 받는다. */
export function usePlaces(filters: PlaceListFilters) {
  return useInfiniteQuery<PlacePage, Error, InfiniteData<PlacePage>, readonly unknown[], number>({
    getNextPageParam: (lastPage) => {
      const nextOffset = lastPage.offset + lastPage.items.length;
      return nextOffset < lastPage.total ? nextOffset : undefined;
    },
    initialPageParam: 0,
    queryFn: ({ pageParam }) => getPlaces(filters, pageParam),
    queryKey: [...placesQueryKey, filters],
  });
}
