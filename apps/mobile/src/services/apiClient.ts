import { create, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { router } from 'expo-router';

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
} from '@/src/features/auth/services/tokenStorage';

export const apiClient = create({
  baseURL: process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1',
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
      // 재발급 실패 → 토큰을 지우고 로그인 화면으로. 토큰이 사라지면 세션 게이트
      // (getAuthSession)도 통과시키지 않는다.
      await clearTokens();
      router.replace('/login');
      return Promise.reject(error);
    }

    original._retry = true;
    original.headers.Authorization = `Bearer ${newAccessToken}`;
    return apiClient(original);
  },
);
