/**
 * 여행기록 서버 호출.
 *
 * 서버와 앱의 타입 차이는 `./travelLogAdapter.ts` 가 흡수한다.
 * 이 파일은 "어디를 부르는가"만 담고, 훅·화면은 수정하지 않는다.
 *
 * 생성은 **"접수했습니다" 방식**이다. 서버가 이미지를 다 만들 때까지 기다리면
 * 화면이 멈춘 것처럼 보이므로, 서버는 202 로 접수만 알리고 앱이
 * `getGenerationStatus` 로 완료를 확인한다.
 *
 * 이미지를 실제로 그리는 부분은 아직 서버에서 임시 구현이라 원본 사진이
 * 그대로 결과물로 온다. 앱이 고칠 것은 없다 — 서버만 바뀌면 된다.
 */

import { apiClient } from '@/src/services/apiClient';
import type { Trip, TravelLog, TravelLogListItem } from '@/src/types/travelLog';

import type { RouteDetailResponse } from '../../trips/types/routeApi';
import type {
  ServerGenerationStatus,
  TravelLogCreateRequest,
  TravelLogGenerationStatusResponse,
  TravelLogGroupsResponse,
  TravelLogItemResponse,
  TravelLogListResponse,
  TravelLogRegenerateRequest,
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

/**
 * 기록 만들기 — POST /travel-logs
 *
 * 서버는 행만 만들고 **202** 로 바로 답한다. 이미지는 뒤에서 만들어지므로
 * 이 함수가 끝났다고 완성된 것이 아니다. `getGenerationStatus` 로 확인한다.
 */
export async function createTravelLog(
  payload: TravelLogCreateRequest,
): Promise<TravelLogGenerationStatusResponse> {
  const { data } = await apiClient.post<TravelLogGenerationStatusResponse>(
    '/travel-logs',
    payload,
  );
  return data;
}

/** 생성 진행 상태 — GET /travel-logs/{logId}/status */
export async function getGenerationStatus(
  logId: string,
): Promise<TravelLogGenerationStatusResponse> {
  const { data } = await apiClient.get<TravelLogGenerationStatusResponse>(
    `/travel-logs/${logId}/status`,
  );
  return data;
}

/**
 * 다시 만들기 — POST /travel-logs/{logId}/regenerate
 *
 * 실패(`failed`)로 남은 기록을 되살리는 길이기도 하다.
 * 원본 사진은 그대로 두고 완성 이미지만 새로 만든다.
 */
export async function regenerateTravelLog(
  logId: string,
  payload: TravelLogRegenerateRequest = {},
): Promise<TravelLogGenerationStatusResponse> {
  const { data } = await apiClient.post<TravelLogGenerationStatusResponse>(
    `/travel-logs/${logId}/regenerate`,
    payload,
  );
  return data;
}

/** 기록 하나 조회 — GET /travel-logs/{logId} */
export async function getTravelLog(logId: string): Promise<TravelLog> {
  const { data } = await apiClient.get<TravelLogItemResponse>(`/travel-logs/${logId}`);
  return toTravelLog(data);
}

/** 완료를 기다리며 다시 물어보는 간격 */
const POLL_INTERVAL_MS = 2_000;

/**
 * 이만큼 지나도 안 끝나면 포기한다.
 *
 * 서버가 재시작되면 진행 중이던 건이 `generating` 에 영영 멈춘다. 제한이 없으면
 * 앱이 그 화면에서 끝없이 돈다. 포기해도 기록은 서버에 남아 있어서
 * 목록의 "다시 만들기"로 이어갈 수 있다.
 */
const POLL_TIMEOUT_MS = 120_000;

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

/**
 * 생성이 끝날 때까지 기다렸다가 완성된 기록을 돌려준다.
 *
 * `onStatus` 로 진행 상태를 알려준다 — 화면이 "사진을 준비하고 있어요" 와
 * "여행의 순간을 기록하고 있어요" 를 바꿔 보여주는 데 쓴다.
 */
export async function waitForGeneration(
  logId: string,
  onStatus?: (status: ServerGenerationStatus) => void,
): Promise<TravelLog> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;

  for (;;) {
    const { generationStatus } = await getGenerationStatus(logId);
    onStatus?.(generationStatus);

    if (generationStatus === 'completed') return getTravelLog(logId);
    if (generationStatus === 'failed') throw new Error('GENERATION_FAILED');
    if (Date.now() >= deadline) throw new Error('GENERATION_TIMEOUT');

    await wait(POLL_INTERVAL_MS);
  }
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
