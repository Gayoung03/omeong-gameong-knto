import type {
  FavoritePlaceListResponse,
  PlaceListResponse,
} from '@/src/features/places/types/placeApi';
import { apiClient } from '@/src/services/apiClient';

import { PLACE_FILTER_CATEGORIES } from '../constants/placeSearch';
import type { PlaceCandidate, PlaceFilter, PlaceSourceTab } from '../types/trip';

import { toPlaceCandidate } from './placeCandidateAdapter';

/**
 * 일정 추가 화면이 쓰는 장소 조회.
 *
 * places 담당 영역과의 관계
 * -------------------------
 * 검색 자체는 places 기능의 몫이지만, '이 날짜 루트 근처' 처럼 여행 정보를 알아야
 * 하는 목록이 섞여 있어 trips 안에서 함께 다룬다. 화면은 장소 ID(`PlaceSelectionResult`)
 * 만 돌려주므로, 나중에 places 검색 화면을 재사용하기로 정해지면 이 파일만 사라진다.
 */

/** 지도에 20개까지 그리고 목록은 스크롤한다. 서버 상한은 100. */
const LIST_LIMIT = 50;

/** 하루 루트 근처. 제주는 한 날짜 안에서도 꽤 움직여서 넉넉히 잡는다. */
const DAY_RADIUS_METERS = 10_000;

/** 숙소 근처. 걸어서 갈 만한 거리 + 차로 몇 분. */
const STAY_RADIUS_METERS = 3_000;

export type PlaceCoordinate = {
  latitude: number;
  longitude: number;
};

function filterByCategory(places: PlaceCandidate[], filter: PlaceFilter | null): PlaceCandidate[] {
  if (!filter) {
    return places;
  }

  const categories = PLACE_FILTER_CATEGORIES[filter];
  return places.filter((place) => categories.includes(place.category));
}

/**
 * 좌표 기준 주변 장소.
 *
 * 좌표를 보내면 서버가 거리를 계산해 가까운 순으로 준다(`sort` 기본값이 `distance`).
 * 분류 필터는 서버에 넘기지 않는다 — 서버 `category` 는 한 번에 하나인데
 * 앱의 '맛집' 칩은 `restaurant` 와 `cafe` 둘을 함께 보기 때문이다.
 */
async function getNearbyPlaces(
  coordinate: PlaceCoordinate,
  radius: number,
): Promise<PlaceCandidate[]> {
  const { data } = await apiClient.get<PlaceListResponse>('/places', {
    params: {
      latitude: coordinate.latitude,
      limit: LIST_LIMIT,
      longitude: coordinate.longitude,
      radius,
    },
  });

  return data.items.map(toPlaceCandidate);
}

async function getAllPlaces(): Promise<PlaceCandidate[]> {
  const { data } = await apiClient.get<PlaceListResponse>('/places', {
    params: { limit: LIST_LIMIT },
  });

  return data.items.map(toPlaceCandidate);
}

/** 최근 저장 = 서버의 즐겨찾기. 기본 정렬이 최근 저장순이라 그대로 쓴다. */
async function getFavoritePlaces(): Promise<PlaceCandidate[]> {
  const { data } = await apiClient.get<FavoritePlaceListResponse>('/users/me/favorites', {
    params: { limit: LIST_LIMIT },
  });

  return data.items.map(toPlaceCandidate);
}

/** 내가 등록한 장소. `GET /places` 에는 안 나오므로 경로가 따로 있다. */
async function getMyPlaces(): Promise<PlaceCandidate[]> {
  const { data } = await apiClient.get<PlaceListResponse>('/users/me/places', {
    params: { limit: LIST_LIMIT },
  });

  return data.items.map(toPlaceCandidate);
}

type GetPlaceCandidatesParams = {
  tab: PlaceSourceTab;
  filter: PlaceFilter | null;
  /** 탭이 기준으로 삼을 좌표. 없으면 탭마다 다르게 처리한다. */
  coordinate: PlaceCoordinate | null;
};

/**
 * 탭별 장소 목록.
 *
 * **추천 알고리즘은 아직 없다.** 남은 엔드포인트 3개가 추천 방식(규칙 vs AI) 결정을
 * 기다리는 중이라, 지금 '추천' 탭은 **그 날짜 일정의 중심 좌표에서 가까운 순**이다.
 * 거리만 보는 것이라 취향·날씨·동반 조건은 반영되지 않는다.
 * 추천 API 가 생기면 `dayRecommend` 갈래만 그쪽으로 바꾼다.
 */
export async function getPlaceCandidates({
  coordinate,
  filter,
  tab,
}: GetPlaceCandidatesParams): Promise<PlaceCandidate[]> {
  const places = await loadByTab(tab, coordinate);
  return filterByCategory(places, filter);
}

function loadByTab(tab: PlaceSourceTab, coordinate: PlaceCoordinate | null) {
  switch (tab) {
    case 'recentSaved':
      return getFavoritePlaces();

    case 'myPlace':
      return getMyPlaces();

    case 'nearStay':
      // 숙소가 일정에 없으면 기준점이 없다. 빈 목록의 안내 문구가
      // "숙소를 먼저 일정에 담으면 근처 장소를 추천해드려요" 라 그대로 맞는다.
      return coordinate ? getNearbyPlaces(coordinate, STAY_RADIUS_METERS) : Promise.resolve([]);

    case 'dayRecommend':
    default:
      // 그 날짜가 아직 비어 있으면 기준점이 없다. 이때는 빈 화면 대신 전체 목록을 준다 —
      // 첫 장소를 담으려고 들어온 사용자에게 아무것도 안 보여주면 할 수 있는 게 없다.
      return coordinate ? getNearbyPlaces(coordinate, DAY_RADIUS_METERS) : getAllPlaces();
  }
}

type SearchPlacesParams = {
  keyword: string;
  filter: PlaceFilter | null;
};

/**
 * 키워드 검색.
 *
 * 서버는 **장소명만** 본다(`Place.name ILIKE`). 예전 목데이터는 설명·지역·주소까지
 * 훑었는데 그 동작은 서버에 없다. 범위를 넓히려면 서버 쪽을 고쳐야 한다.
 */
export async function searchPlaces({
  filter,
  keyword,
}: SearchPlacesParams): Promise<PlaceCandidate[]> {
  const normalized = keyword.trim();

  if (normalized.length === 0) {
    return [];
  }

  const { data } = await apiClient.get<PlaceListResponse>('/places', {
    params: { limit: LIST_LIMIT, q: normalized },
  });

  return filterByCategory(data.items.map(toPlaceCandidate), filter);
}
