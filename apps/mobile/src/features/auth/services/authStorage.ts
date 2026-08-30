import AsyncStorage from '@react-native-async-storage/async-storage';

import { LEGAL_DOCUMENT_VERSION } from '@/src/features/legal/constants/legalDocuments';

import { login, logout, signup, type AuthProvider, type AuthUser } from '../api/authApi';
import { toSignupPayload } from '../api/signupMapping';
import type { SignupAgreements, SignupData } from '../types/auth';

import { clearTokens, getRefreshToken, saveTokens } from './tokenStorage';

const AUTH_SESSION_KEY = 'omeong-gameong.auth-session';
const CONSENT_KEY = 'omeong-gameong.consent-record';

export type AuthSession = {
  /** 예전 앱이 저장한 세션에는 없을 수 있어 읽을 때 이메일로 호환한다. */
  userId?: string;
  email: string;
  nickname: string;
  /** 최초 가입 수단. 회원 탈퇴가 비밀번호(local)냐 제공처 재인증(소셜)이냐를 가른다. */
  authProvider: AuthProvider;
  signedInAt: string;
};

/**
 * 동의 이력. 어떤 항목에 언제 어느 버전으로 동의했는지 남긴다.
 *
 * **아직 기기에만 저장한다.** auth.md signup 명세에는 동의 필드가 없어, 이 값을
 * 서버로 보내는 계약이 없다. `user_consents` 연동은 별도 명세 논의 대상이라, 계약을
 * 임의로 확장하지 않고 기존처럼 로컬 보관만 유지한다(보고에 명시).
 */
export type ConsentRecord = {
  agreements: SignupAgreements;
  documentVersion: string;
  agreedAt: string;
};

export async function getConsentRecord() {
  const value = await AsyncStorage.getItem(CONSENT_KEY);
  return value ? (JSON.parse(value) as ConsentRecord) : null;
}

async function saveConsentRecord(agreements: SignupAgreements) {
  const record: ConsentRecord = {
    agreements,
    documentVersion: LEGAL_DOCUMENT_VERSION,
    agreedAt: new Date().toISOString(),
  };

  await AsyncStorage.setItem(CONSENT_KEY, JSON.stringify(record));
  return record;
}

async function saveSession(user: Pick<AuthUser, 'id' | 'email' | 'nickname' | 'authProvider'>) {
  const session: AuthSession = {
    userId: user.id,
    // 소셜 계정은 email 이 null 일 수 있다. 화면 표시는 닉네임을 쓰므로 빈 문자열로 둔다.
    email: user.email ?? '',
    nickname: user.nickname,
    authProvider: user.authProvider,
    signedInAt: new Date().toISOString(),
  };

  await AsyncStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
  return session;
}

/**
 * 저장된 세션. **refresh 토큰이 없으면 세션도 없는 것으로 본다.**
 *
 * 세션 게이트((tabs)/_layout·LoginScreen)가 이 값으로 로그인 여부를 판단한다.
 * 재발급 실패로 토큰이 지워지면(apiClient) 여기서 null 을 돌려줘 게이트가 로그인
 * 화면으로 보낸다 — 세션 레코드를 따로 지우지 않아도 상태가 어긋나지 않는다.
 */
export async function getAuthSession() {
  const refreshToken = await getRefreshToken();
  if (!refreshToken) return null;

  const value = await AsyncStorage.getItem(AUTH_SESSION_KEY);
  return value ? (JSON.parse(value) as AuthSession) : null;
}

/** 이메일 로그인. 토큰을 저장하고 서버가 준 사용자로 세션을 구성한다. */
export async function signIn(email: string, password: string) {
  const result = await login(email, password);
  await saveTokens(result.accessToken, result.refreshToken);
  return saveSession(result.user);
}

/** 소셜 로그인/연동 완료 후 토큰·세션을 구성한다(카카오 콜백에서 호출). */
export async function completeSocialLogin(result: {
  accessToken: string;
  refreshToken: string;
  user: Pick<AuthUser, 'id' | 'email' | 'nickname' | 'authProvider'>;
}) {
  await saveTokens(result.accessToken, result.refreshToken);
  return saveSession(result.user);
}

/**
 * 계정·(선택)반려동물·여행 취향을 한 요청으로 가입한다.
 *
 * `SignupData` → auth.md 페이로드 변환은 `toSignupPayload` 가 한다. 동의 이력은
 * 서버 계약이 없어 기존처럼 로컬에만 남긴다.
 */
export async function completeSignup(data: SignupData) {
  const result = await signup(toSignupPayload(data));
  await saveTokens(result.accessToken, result.refreshToken);
  await saveConsentRecord(data.agreements);
  return saveSession(result.user);
}

/**
 * 저장된 세션의 닉네임을 바꾼다.
 *
 * 마이페이지에서 닉네임을 수정하면 화면 상태만 바뀌고 세션은 이전 값을 들고 있어,
 * 앱을 다시 켰을 때 수정 전 이름으로 되돌아간다. 그것을 막기 위해 함께 갱신한다.
 */
export async function updateSessionNickname(nickname: string) {
  const value = await AsyncStorage.getItem(AUTH_SESSION_KEY);
  if (!value) return null;

  const session = JSON.parse(value) as AuthSession;
  const updated: AuthSession = { ...session, nickname };
  await AsyncStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(updated));
  return updated;
}

/**
 * 로그인 상태를 기기에서 모두 지운다(토큰·세션·동의기록).
 *
 * 수동 로그아웃(signOut)·강제 로그아웃(apiClient 재발급 실패)·회원 탈퇴가 **같은
 * 집합**을 지우도록 한곳에 모았다. queryClient 캐시 비우기는 React 컨텍스트가 필요해
 * 여기서 하지 않고 호출부(useLogout·apiClient)가 함께 처리한다.
 */
export async function clearAuthState() {
  await clearTokens();
  await AsyncStorage.multiRemove([AUTH_SESSION_KEY, CONSENT_KEY]);
}

/** 로그아웃. 서버 로그아웃은 무효화가 없어 성공 신호일 뿐이라, 실패해도 로컬은 지운다. */
export async function signOut() {
  try {
    await logout();
  } catch {
    // 서버 로그아웃 실패(네트워크 등)해도 기기의 토큰·세션·동의기록은 반드시 지운다.
  }
  await clearAuthState();
}

/** 회원 탈퇴 시 기기에 남은 계정 관련 기록을 모두 지운다(로그아웃 정리와 같은 집합). */
export async function clearAccountStorage() {
  await clearAuthState();
}
