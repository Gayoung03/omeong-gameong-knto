import { create, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { router } from 'expo-router';

import { getAccessToken, getRefreshToken, saveTokens } from '@/src/features/auth/services/tokenStorage';

import { queryClient } from './queryClient';

const API_URL = process.env.EXPO_PUBLIC_API_URL;

// 프로덕션 빌드에 API URL 이 없으면 localhost 로 몰래 붙는 대신 즉시 실패시킨다.
// (dev 는 localhost 폴백을 허용한다.)
if (!API_URL && !__DEV__) {
  throw new Error('EXPO_PUBLIC_API_URL 이 설정되지 않았습니다 — 프로덕션 빌드에는 필수입니다.');
}

export const apiClient = create({
  baseURL: API_URL ?? 'http://localhost:8000/api/v1',
  timeout: 10_000,
});

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

// 저장된 access 토큰을 매 요청 Authorization 헤더에 싣는다.
apiClient.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/**
 * 진행 중인 재발급을 공유한다.
 *
 * access 토큰이 만료되면 여러 요청이 동시에 401 을 받는다. 각자 refresh 를 내보내면
 * 재발급이 여러 번 나가고, 무회전이라 문제는 없지만 낭비다(auth.md: "재발급 요청이
 * 한 번만 나가도록 묶어야 한다"). 첫 401 이 만든 Promise 를 나머지가 함께 기다린다.
 */
let refreshPromise: Promise<string | null> | null = null;

async function runRefresh(): Promise<string | null> {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) return null;
  try {
    const { data } = await apiClient.post<{ accessToken: string; refreshToken: string }>(
      '/auth/refresh',
      { refreshToken },
    );
    // 무회전 — refreshToken 은 보낸 값이 그대로 돌아온다. 그대로 다시 저장한다.
    await saveTokens(data.accessToken, data.refreshToken);
    return data.accessToken;
  } catch {
    return null;
  }
}

/**
 * 재발급 실패 시 강제 로그아웃. 수동 로그아웃과 **동일하게** 토큰·세션·동의기록을 지우고
 * 쿼리 캐시를 비운 뒤 로그인 화면으로 보낸다. authStorage 를 정적 import 하면 순환이
 * 생기므로(authStorage→authApi→apiClient) 동적 import 로 끊는다.
 */
async function forceLogout(): Promise<void> {
  const { clearAuthState } = await import('@/src/features/auth/services/authStorage');
  await clearAuthState();
  queryClient.clear();
  router.replace('/login');
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    const status = error.response?.status;

    // `/auth/*` 의 401 은 정상 흐름이다(로그인 실패·토큰 무효 등). 재발급하지 않고
    // 그대로 올려 화면이 사유를 처리하게 둔다. 재시도한 요청(_retry)도 그대로 올린다.
    const isAuthRequest = original?.url?.startsWith('/auth/') ?? false;
    if (status !== 401 || !original || original._retry || isAuthRequest) {
      return Promise.reject(error);
    }

    if (!refreshPromise) {
      refreshPromise = runRefresh().finally(() => {
        refreshPromise = null;
      });
    }
    const newAccessToken = await refreshPromise;

    if (!newAccessToken) {
      // 재발급 실패 → 수동 로그아웃과 동일하게 정리하고 로그인 화면으로.
      await forceLogout();
      return Promise.reject(error);
    }

    original._retry = true;
    original.headers.Authorization = `Bearer ${newAccessToken}`;
    return apiClient(original);
  },
);
