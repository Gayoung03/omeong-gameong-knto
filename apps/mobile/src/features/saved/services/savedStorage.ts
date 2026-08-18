import AsyncStorage from '@react-native-async-storage/async-storage';

import { getAuthSession } from '@/src/features/auth/services/authStorage';

import type { SavedPlace, SavedRoute } from '../types/saved';

const PLACES_KEY_PREFIX = 'omeong-gameong.saved-places';
const ROUTES_KEY_PREFIX = 'omeong-gameong.saved-routes';
/** 로그인 전에 저장한 항목이 담기는 자리. */
const GUEST_SCOPE = 'guest';

/**
 * 저장 목록은 로그아웃해도 기기에 남긴다(팀 결정).
 * 다만 키에 계정을 물려 다른 계정으로 로그인했을 때 남의 목록이 보이지 않게 한다.
 *
 * TODO: 저장 API 가 준비되면 이 파일의 구현만 서버 호출로 갈아끼운다.
 *       호출부(hooks)는 그대로 두는 것이 목표다.
 */
async function scopedKey(prefix: string) {
  const session = await getAuthSession();
  return `${prefix}.${session?.email ?? GUEST_SCOPE}`;
}

async function readList<T>(prefix: string): Promise<T[]> {
  try {
    const raw = await AsyncStorage.getItem(await scopedKey(prefix));
    if (!raw) return [];

    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as T[]) : [];
  } catch {
    // 저장된 값이 깨졌을 때 앱이 멈추지 않도록 빈 목록으로 되돌린다.
    return [];
  }
}

async function writeList<T>(prefix: string, list: T[]) {
  await AsyncStorage.setItem(await scopedKey(prefix), JSON.stringify(list));
}

export async function getSavedPlaces(): Promise<SavedPlace[]> {
  return readList<SavedPlace>(PLACES_KEY_PREFIX);
}

/** 이미 저장돼 있으면 지우고, 없으면 넣는다. 저장된 상태를 돌려준다. */
export async function toggleSavedPlace(place: Omit<SavedPlace, 'savedAt'>): Promise<boolean> {
  const list = await getSavedPlaces();
  const exists = list.some((item) => item.id === place.id);

  const next = exists
    ? list.filter((item) => item.id !== place.id)
    : [{ ...place, savedAt: new Date().toISOString() }, ...list];

  await writeList(PLACES_KEY_PREFIX, next);
  return !exists;
}

export async function removeSavedPlace(placeId: string) {
  const list = await getSavedPlaces();
  await writeList(
    PLACES_KEY_PREFIX,
    list.filter((item) => item.id !== placeId),
  );
}

export async function getSavedRoutes(): Promise<SavedRoute[]> {
  return readList<SavedRoute>(ROUTES_KEY_PREFIX);
}

/** 같은 id 가 있으면 최신 내용으로 갈아끼우고 맨 앞으로 올린다. */
export async function addSavedRoute(route: SavedRoute) {
  const list = await getSavedRoutes();
  await writeList(ROUTES_KEY_PREFIX, [route, ...list.filter((item) => item.id !== route.id)]);
}

export async function removeSavedRoute(routeId: string) {
  const list = await getSavedRoutes();
  await writeList(
    ROUTES_KEY_PREFIX,
    list.filter((item) => item.id !== routeId),
  );
}
