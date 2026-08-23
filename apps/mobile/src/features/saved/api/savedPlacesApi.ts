import { toPlace } from '@/src/features/places/api/placeAdapter';
import type { FavoritePlaceListResponse } from '@/src/features/places/types/placeApi';
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

const LIST_LIMIT = 100;

export async function getSavedPlaces(): Promise<SavedPlace[]> {
  const { data } = await apiClient.get<FavoritePlaceListResponse>('/users/me/favorites', {
    params: { limit: LIST_LIMIT },
  });

  return data.items.map((item) => {
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
  });
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
