import { PLACE_FILTER_CATEGORIES } from '../constants/placeSearch';
import { MOCK_CANDIDATE_IDS_BY_TAB, MOCK_PLACE_CANDIDATES } from '../mocks/placeCandidates.mock';
import type { PlaceCandidate, PlaceFilter, PlaceSourceTab } from '../types/trip';

/**
 * 일정 추가 화면이 쓰는 장소 조회.
 *
 * 백엔드 /api/v1/places 가 준비되기 전까지 Mock 데이터를 반환한다.
 * API 연동 시 이 파일의 구현만 apiClient 호출로 교체하고, Hook·화면은 수정하지 않는다.
 *
 * places 담당 영역과의 관계
 * -------------------------
 * 검색은 원래 places 기능의 몫이다. 다만 '이 날짜 루트 근처 추천'처럼
 * 여행 정보를 알아야 하는 목록이 섞여 있어 우선 trips 안에서 함께 다룬다.
 * 나중에 places 검색 화면을 재사용하기로 정해지면 `searchPlaces` 만
 * 그쪽 API 로 바꾸고, 화면은 장소 ID(`PlaceSelectionResult`)만 돌려받으면 된다.
 */
const MOCK_DELAY_MS = 300;

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), MOCK_DELAY_MS);
  });
}

function filterByCategory(places: PlaceCandidate[], filter: PlaceFilter | null): PlaceCandidate[] {
  if (!filter) {
    return places;
  }

  const categories = PLACE_FILTER_CATEGORIES[filter];
  return places.filter((place) => categories.includes(place.category));
}

type GetPlaceCandidatesParams = {
  tab: PlaceSourceTab;
  filter: PlaceFilter | null;
};

/** 탭별 추천 장소 목록 */
export async function getPlaceCandidates({
  tab,
  filter,
}: GetPlaceCandidatesParams): Promise<PlaceCandidate[]> {
  const ids = MOCK_CANDIDATE_IDS_BY_TAB[tab];
  const places = ids
    .map((id) => MOCK_PLACE_CANDIDATES.find((place) => place.id === id))
    .filter((place): place is PlaceCandidate => place !== undefined);

  return delay(filterByCategory(places, filter));
}

type SearchPlacesParams = {
  keyword: string;
  filter: PlaceFilter | null;
};

/** 키워드 검색. 이름·설명·지역을 함께 본다 */
export async function searchPlaces({
  keyword,
  filter,
}: SearchPlacesParams): Promise<PlaceCandidate[]> {
  const normalized = keyword.trim().toLowerCase();

  if (normalized.length === 0) {
    return delay([]);
  }

  const matched = MOCK_PLACE_CANDIDATES.filter((place) =>
    [place.name, place.description, place.regionLabel, place.address].some((text) =>
      text.toLowerCase().includes(normalized),
    ),
  );

  return delay(filterByCategory(matched, filter));
}

/** 장소 단건 조회. 선택 결과로 ID 만 받았을 때 사용한다 */
export async function getPlaceCandidate(placeId: string): Promise<PlaceCandidate> {
  const place = MOCK_PLACE_CANDIDATES.find((candidate) => candidate.id === placeId);

  if (!place) {
    throw new Error(`장소를 찾을 수 없습니다. placeId: ${placeId}`);
  }

  return delay(place);
}
