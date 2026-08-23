import { apiClient } from '@/src/services/apiClient';

import type { TripMemo } from '../types/trip';

/**
 * 여행 메모 서버 호출.
 *
 * 앱의 `TripMemo.scheduleId` 가 서버의 `routeDayId` 다.
 * 서버에서 `routeDayId` 가 null 이면 여행 전체 메모인데, 지금 화면은
 * Day 별 메모만 다루므로 그런 메모는 목록에서 걸러낸다.
 */

type MemoResponse = {
  id: string;
  routeDayId: string | null;
  title: string | null;
  content: string;
  createdAt: string;
  updatedAt: string;
};

type MemoListResponse = {
  items: MemoResponse[];
  total: number;
  limit: number;
  offset: number;
};

function toTripMemo(response: MemoResponse): TripMemo {
  return {
    content: response.content,
    id: response.id,
    scheduleId: response.routeDayId as string,
    title: response.title ?? '',
  };
}

export async function getTripMemos(tripId: string): Promise<TripMemo[]> {
  const { data } = await apiClient.get<MemoListResponse>(`/routes/${tripId}/memos`, {
    params: { limit: 100 },
  });

  return data.items.filter((memo) => memo.routeDayId !== null).map(toTripMemo);
}

export async function createTripMemo(
  tripId: string,
  payload: { scheduleId: string; title: string; content: string },
): Promise<TripMemo> {
  const { data } = await apiClient.post<MemoResponse>(`/routes/${tripId}/memos`, {
    content: payload.content,
    routeDayId: payload.scheduleId,
    title: payload.title || null,
  });
  return toTripMemo(data);
}

/** `routeDayId` 는 못 바꾼다. 다른 일차로 옮기려면 지우고 다시 쓴다(명세). */
export async function updateTripMemo(
  memoId: string,
  payload: { title: string; content: string },
): Promise<TripMemo> {
  const { data } = await apiClient.patch<MemoResponse>(`/memos/${memoId}`, {
    content: payload.content,
    title: payload.title || null,
  });
  return toTripMemo(data);
}

export async function removeTripMemo(memoId: string): Promise<void> {
  await apiClient.delete(`/memos/${memoId}`);
}
