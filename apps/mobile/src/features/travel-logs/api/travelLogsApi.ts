/**
 * 여행기록 서버 호출.
 *
 * 서버와 앱의 타입 차이는 `./travelLogAdapter.ts` 가 흡수한다.
 * 이 파일은 "어디를 부르는가"만 담고, 훅·화면은 수정하지 않는다.
 *
 * 아직 서버에 없는 것 — **기록 생성(`POST /travel-logs`)**.
 * AI 이미지 생성을 무엇으로 할지 정해지지 않아 만들기 흐름은 여전히
 * `../services/mockLogService.ts` 를 쓴다.
 */

import { apiClient } from '@/src/services/apiClient';
import type { Trip, TravelLog, TravelLogListItem } from '@/src/types/travelLog';

import type { RouteDetailResponse } from '../../trips/types/routeApi';
import type {
  TravelLogGroupsResponse,
  TravelLogItemResponse,
  TravelLogListResponse,
  TravelLogUpdateRequest,
} from '../types/travelLogApi';
import { toTravelLog, toTravelLogListItem } from './travelLogAdapter';

/** 여행 단위·월 단위로 묶인 목록 — GET /travel-logs/groups */
export async function getTravelLogGroups(): Promise<TravelLogListItem[]> {
  const { data } = await apiClient.get<TravelLogGroupsResponse>('/travel-logs/groups');
  return data.items.map(toTravelLogListItem);
}

/**
 * 여행 모아보기 화면의 헤더 — GET /routes/{tripId}
 *
 * 여행기록이 아니라 **여행** 창구를 부르는 게 맞다. 제목·기간은 여행 쪽
 * 데이터이기 때문이다(docs/api/travel-logs.md "여행 모아보기 화면 구성").
 * 기록 수(`logCount`)도 이 응답이 계산해 내려준다.
 *
 * 이 화면의 `Trip` 은 여행 기능의 `Trip`(features/trips/types/trip.ts)과
 * **다른 타입**이라 `routeAdapter` 를 쓸 수 없다. 필요한 다섯 값만 옮긴다.
 */
export async function getTripHeader(tripId: string): Promise<Trip> {
  const { data } = await apiClient.get<RouteDetailResponse>(`/routes/${tripId}`);

  return {
    tripId: data.id,
    title: data.title,
    // 이 화면은 장소명 검색을 하지 않는다. 목록 화면의 Trip 만 쓰는 값이다.
    placeName: '',
    // startAt·endAt 은 시각(`2026-09-11T09:00:00+09:00`)이고 앱은 날짜만 쓴다.
    startDate: data.startAt.slice(0, 10),
    endDate: data.endAt.slice(0, 10),
    // 여행 쪽 응답에는 프로필 사진이 없다. 이름만으로도 화면은 그려진다.
    companions: data.pets.map((pet) => ({ petId: pet.id, nameSnapshot: pet.name })),
    logCount: data.logCount,
    // 헤더는 미리보기를 그리지 않는다. 본문은 getTripLogs 가 따로 불러온다.
    previewLogs: [],
  };
}

/** 여행 하나에 속한 기록 전부 — GET /travel-logs?routeId={tripId} */
export async function getTripLogs(tripId: string): Promise<TravelLog[]> {
  const { data } = await apiClient.get<TravelLogListResponse>('/travel-logs', {
    params: { routeId: tripId, limit: 100 },
  });
  return data.items.map(toTravelLog);
}

/** 나의 한 줄 수정 — PATCH /travel-logs/{logId} */
export async function updatePersonalMessage(
  logId: string,
  message: string | null,
): Promise<TravelLog> {
  const body: TravelLogUpdateRequest = { personalMessage: message };
  const { data } = await apiClient.patch<TravelLogItemResponse>(
    `/travel-logs/${logId}`,
    body,
  );
  return toTravelLog(data);
}
