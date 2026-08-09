import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { getPlaceCandidates, searchPlaces } from '../api/placeSearchApi';
import type { PlaceFilter, PlaceSourceTab } from '../types/trip';

export const placeSearchQueryKeys = {
  all: ['places'] as const,
  candidates: (tab: PlaceSourceTab, filter: PlaceFilter | null) =>
    [...placeSearchQueryKeys.all, 'candidates', tab, filter] as const,
  search: (keyword: string, filter: PlaceFilter | null) =>
    [...placeSearchQueryKeys.all, 'search', keyword, filter] as const,
};

/** 탭별 추천 장소 목록 */
export function usePlaceCandidates(tab: PlaceSourceTab, filter: PlaceFilter | null) {
  return useQuery({
    queryKey: placeSearchQueryKeys.candidates(tab, filter),
    queryFn: () => getPlaceCandidates({ tab, filter }),
    // 탭·필터를 바꿀 때 목록이 잠깐 비면서 지도가 두 번 다시 그려지는 것을 막는다
    placeholderData: keepPreviousData,
  });
}

/**
 * 키워드 검색 결과.
 *
 * 입력할 때마다 조회하지 않고, 검색을 확정한 키워드만 받는다.
 * (디바운스를 두려면 effect 안에서 setState 를 해야 하는데 ESLint 규칙이 이를 막는다)
 */
export function usePlaceSearchResults(keyword: string, filter: PlaceFilter | null) {
  return useQuery({
    queryKey: placeSearchQueryKeys.search(keyword, filter),
    queryFn: () => searchPlaces({ keyword, filter }),
    enabled: keyword.trim().length > 0,
    placeholderData: keepPreviousData,
  });
}
