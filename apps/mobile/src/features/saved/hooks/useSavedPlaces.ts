import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';

import { getSavedPlaces, removeSavedPlace, toggleSavedPlace } from '../api/savedPlacesApi';

export const savedPlacesQueryKey = ['saved', 'places'] as const;

export function useSavedPlaces() {
  return useQuery({
    queryFn: getSavedPlaces,
    queryKey: savedPlacesQueryKey,
  });
}

/** 화면에서 하트 상태를 빠르게 판별하기 위한 id 집합. */
export function useSavedPlaceIds() {
  const { data: savedPlaces = [] } = useSavedPlaces();

  return useMemo(() => new Set(savedPlaces.map((place) => place.id)), [savedPlaces]);
}

export function useToggleSavedPlace() {
  const queryClient = useQueryClient();

  return useMutation({
    // 지금 저장돼 있는지는 화면이 알고 있다. 서버가 다시 조회하지 않게 함께 보낸다.
    mutationFn: (variables: { placeId: string; isSaved: boolean }) => toggleSavedPlace(variables),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: savedPlacesQueryKey }),
  });
}

export function useRemoveSavedPlace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (placeId: string) => removeSavedPlace(placeId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: savedPlacesQueryKey }),
  });
}
