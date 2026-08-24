import { isAxiosError } from 'axios';

import { apiClient } from '@/src/services/apiClient';

import type { PlaceDetail } from '../types/placeDetail';
import type { PlaceDetailResponse, PlaceListResponse } from '../types/placeApi';
import type { Place } from '../types/place';

import { toPlace, toPlaceDetail } from './placeAdapter';

/** 제주도 장소 수가 많지 않아 한 번에 받아 화면에서 거른다. */
const LIST_LIMIT = 100;

/**
 * 공식 장소 목록.
 *
 * 사용자가 등록한 "나만의 장소"는 여기 나오지 않는다. 서버가 경로를 나눠뒀다
 * (`GET /users/me/places`). 조건을 빠뜨리면 남이 등록한 장소가 이름·좌표째로
 * 섞이는 구조라, 섞일 수 없게 막아둔 것이다.
 */
export async function getPlaces(): Promise<Place[]> {
  const { data } = await apiClient.get<PlaceListResponse>('/places', {
    params: { limit: LIST_LIMIT },
  });

  return data.items.map(toPlace);
}

/**
 * 장소 상세 조회.
 *
 * **없는 장소는 오류가 아니라 `null` 이다.** 화면이 "장소를 찾을 수 없어요" 를
 * 그리는 경로가 이미 있어서, 404 를 예외로 올리면 같은 상황을 두 갈래로 다루게 된다.
 * 그 밖의 오류(네트워크·500)는 그대로 올려 재시도 화면이 뜨게 둔다.
 *
 * 남이 등록한 "나만의 장소" id 로 직접 요청해도 404 다 — 서버가 소유자만 보게 막는다.
 */
export async function getPlaceDetail(placeId: string): Promise<PlaceDetail | null> {
  try {
    const { data } = await apiClient.get<PlaceDetailResponse>(`/places/${placeId}`);
    return toPlaceDetail(data);
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === 404) {
      return null;
    }

    throw error;
  }
}
