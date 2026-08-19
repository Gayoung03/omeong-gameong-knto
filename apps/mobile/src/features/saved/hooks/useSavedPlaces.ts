import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';

import { getSavedPlaces, removeSavedPlace, toggleSavedPlace } from '../services/savedStorage';
import type { SavedPlace } from '../types/saved';

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
    mutationFn: (place: Omit<SavedPlace, 'savedAt'>) => toggleSavedPlace(place),
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
