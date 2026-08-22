import { apiClient } from '@/src/services/apiClient';

import type { RouteDetailResponse, RouteListResponse } from '../types/routeApi';
import type { Trip, TripListItem } from '../types/trip';
import { toTrip, toTripListItem } from './routeAdapter';

/**
 * 내 여행 서버 호출.
 *
 * 서버와 앱의 타입 차이는 `./routeAdapter.ts` 가 흡수한다.
 * 이 파일은 "어디를 부르는가"만 담고, Hook·화면은 수정하지 않는다.
 *
 * 주소가 `/trips` 가 아니라 **`/routes`** 다 — 서버의 `trips.py` 는 여행기록(travel_logs) 담당이다.
 */

/** 내 여행 목록 조회 */
export async function getTrips(): Promise<TripListItem[]> {
  const { data } = await apiClient.get<RouteListResponse>('/routes');
  return data.items.map(toTripListItem);
}

/** 여행 상세 조회 */
export async function getTrip(tripId: string): Promise<Trip> {
  const { data } = await apiClient.get<RouteDetailResponse>(`/routes/${tripId}`);
  return toTrip(data);
}

/**
 * 가장 최근 여행 조회. 목록이 비어 있으면 null.
 *
 * 서버가 `startAt` 내림차순으로 주므로 첫 줄이 가장 최근이다.
 * 목록에는 일정이 없어서 그 id 로 상세를 한 번 더 부른다.
 */
export async function getLatestTrip(): Promise<Trip | null> {
  const { data } = await apiClient.get<RouteListResponse>('/routes', {
    params: { limit: 1 },
  });

  const latest = data.items[0];
  return latest ? getTrip(latest.id) : null;
}
