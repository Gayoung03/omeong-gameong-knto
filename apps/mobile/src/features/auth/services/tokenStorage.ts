import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/**
 * access / refresh 토큰 저장소.
 *
 * 네이티브는 `expo-secure-store`(키체인·키스토어)에 둔다. **웹은 secure-store 가
 * 동작하지 않아** `localStorage` 로 폴백한다(auth.md 는 두 토큰을 모두 저장하라고 한다).
 * localStorage 는 secure-store 만큼 안전하지 않지만, 웹은 데모·심사 범위이고 대안이
 * 마땅치 않다 — 저장 위치만 갈리고 나머지 흐름은 동일하다.
 *
 * 토큰 값 자체는 어디에도 로그로 남기지 않는다.
 */
const ACCESS_TOKEN_KEY = 'omeong-gameong.access-token';
const REFRESH_TOKEN_KEY = 'omeong-gameong.refresh-token';

const isWeb = Platform.OS === 'web';

async function setItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function getItem(key: string): Promise<string | null> {
  if (isWeb) {
    return globalThis.localStorage?.getItem(key) ?? null;
  }
  return SecureStore.getItemAsync(key);
}

async function removeItem(key: string): Promise<void> {
  if (isWeb) {
    globalThis.localStorage?.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export async function saveTokens(accessToken: string, refreshToken: string): Promise<void> {
  await Promise.all([
    setItem(ACCESS_TOKEN_KEY, accessToken),
    setItem(REFRESH_TOKEN_KEY, refreshToken),
  ]);
}

export async function getAccessToken(): Promise<string | null> {
  return getItem(ACCESS_TOKEN_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  return getItem(REFRESH_TOKEN_KEY);
}

export async function clearTokens(): Promise<void> {
  await Promise.all([removeItem(ACCESS_TOKEN_KEY), removeItem(REFRESH_TOKEN_KEY)]);
}
