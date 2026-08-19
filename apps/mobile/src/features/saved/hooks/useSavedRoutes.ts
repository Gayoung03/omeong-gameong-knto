import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { addSavedRoute, getSavedRoutes, removeSavedRoute } from '../services/savedStorage';
import type { SavedRoute } from '../types/saved';

export const savedRoutesQueryKey = ['saved', 'routes'] as const;

export function useSavedRoutes() {
  return useQuery({
    queryFn: getSavedRoutes,
    queryKey: savedRoutesQueryKey,
  });
}

export function useSaveRoute() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (route: SavedRoute) => addSavedRoute(route),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: savedRoutesQueryKey }),
  });
}

export function useRemoveSavedRoute() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (routeId: string) => removeSavedRoute(routeId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: savedRoutesQueryKey }),
  });
}
