import { toPlace } from '@/src/features/places/api/placeAdapter';
import type {
  FavoritePlaceListResponse,
  FavoritePlaceResponse,
} from '@/src/features/places/types/placeApi';
import { apiClient } from '@/src/services/apiClient';

import type { SavedPlace } from '../types/saved';

/**
 * 저장한 장소 = 서버의 즐겨찾기.
 *
 * 예전에는 AsyncStorage 에 두었다(`services/savedStorage.ts`). 기기를 바꾸면
 * 사라지고 다른 기기와도 따로 놀았다. 이제 계정을 따라간다.
 *
 * **저장한 코스(route)는 아직 기기에 남는다** — 서버에 그 API 가 없다.
 * 그래서 savedStorage.ts 가 코스 쪽만 들고 남아 있다.
 */

/** 서버가 한 번에 내주는 최대치(`le=100`). 더 크게 보내면 422 다. */
const PAGE_LIMIT = 100;

function toSavedPlace(item: FavoritePlaceResponse): SavedPlace {
  // 분류 라벨·주소 정리는 장소 어댑터가 이미 한다. 두 번 쓰면 화면마다 달라진다.
  const place = toPlace(item);

  return {
    address: place.address,
    category: place.category,
    id: place.id,
    imageUrl: place.imageUrl,
    name: place.name,
    savedAt: item.favoritedAt,
  };
}

function fetchPage(offset: number) {
  return apiClient
    .get<FavoritePlaceListResponse>('/users/me/favorites', {
      params: { limit: PAGE_LIMIT, offset },
    })
    .then((response) => response.data);
}

/**
 * 저장한 장소 **전부**.
 *
 * 예전에는 한 페이지(100건)만 받아서 101번째부터는 화면에 아예 나오지 않았다.
 * 즐겨찾기는 지우기 전까지 쌓이기만 하므로 언젠가 반드시 넘는다.
 *
 * 첫 페이지의 `total` 로 남은 offset 을 계산해 **병렬로** 받는다. 순차로 돌면
 * 왕복이 그대로 쌓인다. 100건 이하면 요청은 예전과 같이 한 번이다.
 */
export async function getSavedPlaces(): Promise<SavedPlace[]> {
  const firstPage = await fetchPage(0);

  const restOffsets: number[] = [];
  for (let offset = PAGE_LIMIT; offset < firstPage.total; offset += PAGE_LIMIT) {
    restOffsets.push(offset);
  }
  const restPages = await Promise.all(restOffsets.map(fetchPage));

  // 서버 정렬이 저장 시각 내림차순이라, 받는 도중 다른 기기에서 하트를 누르면
  // 뒤 페이지가 한 칸 밀려 같은 장소가 두 번 온다. 중복 key 로 목록이 깨지는 쪽이
  // 한 건 누락보다 나쁘므로 id 로 한 번 거른다.
  const seenIds = new Set<string>();

  return [firstPage, ...restPages]
    .flatMap((page) => page.items)
    .filter((item) => {
      if (seenIds.has(item.id)) return false;
      seenIds.add(item.id);
      return true;
    })
    .map(toSavedPlace);
}

export async function addSavedPlace(placeId: string) {
  // PUT 이라 여러 번 눌러도 결과가 같다. 이미 저장된 장소여도 204 다.
  await apiClient.put(`/places/${placeId}/favorite`);
}

export async function removeSavedPlace(placeId: string) {
  await apiClient.delete(`/places/${placeId}/favorite`);
}

/**
 * 하트 토글. 저장된 상태를 돌려준다.
 *
 * 서버에 토글 엔드포인트는 없다. **지금 저장돼 있는지는 화면이 알고 있으므로**
 * 그 값을 받아 등록·해제 중 하나를 부른다. 서버가 판단하게 만들면 조회가 한 번 더 든다.
 */
export async function toggleSavedPlace({
  isSaved,
  placeId,
}: {
  placeId: string;
  isSaved: boolean;
}): Promise<boolean> {
  if (isSaved) {
    await removeSavedPlace(placeId);
    return false;
  }

  await addSavedPlace(placeId);
  return true;
}
