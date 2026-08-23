import { apiClient } from '@/src/services/apiClient';

import type {
  RouteDetailResponse,
  RouteItemCreateRequest,
  RouteItemResponse,
  RouteListResponse,
} from '../types/routeApi';
import type { Trip, TripListItem } from '../types/trip';
import { toTrip, toTripListItem } from './routeAdapter';

/**
 * 내 여행 서버 호출.
 *
 * 서버와 앱의 타입 차이는 `./routeAdapter.ts` 가 흡수한다.
 * 이 파일은 "어디를 부르는가"만 담고, Hook·화면은 수정하지 않는다.
 *
 * 주소가 `/trips` 가 아니라 **`/routes`** 다 — 서버의 `trips.py` 는 여행기록(travel_logs) 담당이다.
 *
 * `getLatestTrip` 은 목록 화면(`MyTripsScreen`)이 생기면서 없앴다.
 * 목록에서 골라 들어가므로 "가장 최근 여행 하나"를 따로 집어줄 필요가 없다.
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

/** 일정 항목 추가 — POST /route-days/{routeDayId}/items */
export async function addRouteItem(
  scheduleId: string,
  payload: RouteItemCreateRequest,
): Promise<RouteItemResponse> {
  const { data } = await apiClient.post<RouteItemResponse>(
    `/route-days/${scheduleId}/items`,
    payload,
  );
  return data;
}

/** 일정 항목 삭제 — DELETE /route-items/{routeItemId} */
export async function removeRouteItem(itemId: string): Promise<void> {
  await apiClient.delete(`/route-items/${itemId}`);
}

/**
 * 일정 순서 변경 — PUT /route-days/{routeDayId}/items/order
 *
 * **그 날짜의 항목 전체를 순서대로** 보내야 한다. 하나씩 PATCH 하면
 * UNIQUE(route_day_id, sort_order) 때문에 중간 상태에서 충돌한다.
 */
export async function reorderRouteItems(
  scheduleId: string,
  itemIds: string[],
): Promise<void> {
  await apiClient.put(`/route-days/${scheduleId}/items/order`, { itemIds });
}

/**
 * 서버 응답 그대로의 여행 상세.
 *
 * 순서를 저장할 때 필요하다 — 어댑터는 좌표 없는 일정을 걸러내지만
 * 서버에는 남아 있어서, 걸러진 것까지 알아야 "전체를 순서대로" 보낼 수 있다.
 */
export async function getTripRaw(tripId: string): Promise<RouteDetailResponse> {
  const { data } = await apiClient.get<RouteDetailResponse>(`/routes/${tripId}`);
  return data;
}
