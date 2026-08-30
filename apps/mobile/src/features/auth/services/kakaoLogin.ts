import * as Linking from 'expo-linking';
import { Platform } from 'react-native';

/**
 * 카카오 로그인 시작 — 서버 콜백 방식(docs/api/auth.md 소셜 절).
 *
 * 서버의 `/auth/kakao/authorize` 로 보내면 서버가 카카오 로그인 페이지로 302 한다.
 * 로그인이 끝나면 서버가 `returnUrl?code=<교환코드>` 로 되돌려보내고, 앱은
 * `/auth/callback` 라우트에서 그 code 를 교환한다.
 *
 * `expo-web-browser`(openAuthSessionAsync)가 설치돼 있지 않고 패키지 추가가 막혀 있어,
 * 이미 있는 `expo-linking` 으로 시스템 브라우저를 열고 **딥링크 복귀**로 받는다.
 * returnUrl 은 네이티브에서 앱 스킴(`Linking.createURL`), 웹에서 현재 오리진이다.
 */
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export function buildKakaoAuthorizeUrl(returnUrl: string): string {
  return `${API_BASE_URL}/auth/kakao/authorize?returnUrl=${encodeURIComponent(returnUrl)}`;
}

export function startKakaoLogin(): void {
  if (Platform.OS === 'web') {
    const returnUrl = `${globalThis.location.origin}/auth/callback`;
    globalThis.location.href = buildKakaoAuthorizeUrl(returnUrl);
    return;
  }

  // exp://…/--/auth/callback (Expo Go) 또는 omeonggameong://auth/callback (스탠드얼론).
  const returnUrl = Linking.createURL('auth/callback');
  void Linking.openURL(buildKakaoAuthorizeUrl(returnUrl));
}
