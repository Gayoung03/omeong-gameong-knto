import AsyncStorage from '@react-native-async-storage/async-storage';

import type { RouteRequestCreateRequest } from '@/src/features/trips/types/routeApi';

const PENDING_ROUTE_KEY = 'route-recommendation-pending';
const MAX_AGE_MS = 24 * 60 * 60 * 1000;

export type PendingRoute = {
  routeId: string;
  startedAt: number;
  request?: RouteRequestCreateRequest;
};

export async function savePendingRoute(value: PendingRoute): Promise<void> {
  await AsyncStorage.setItem(PENDING_ROUTE_KEY, JSON.stringify(value));
}

export async function loadPendingRoute(): Promise<PendingRoute | null> {
  const raw = await AsyncStorage.getItem(PENDING_ROUTE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as PendingRoute;
    if (!parsed.routeId || Date.now() - parsed.startedAt > MAX_AGE_MS) {
      await clearPendingRoute();
      return null;
    }
    return parsed;
  } catch {
    await clearPendingRoute();
    return null;
  }
}

export async function clearPendingRoute(): Promise<void> {
  await AsyncStorage.removeItem(PENDING_ROUTE_KEY);
}
