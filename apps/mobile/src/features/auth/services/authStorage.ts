import AsyncStorage from '@react-native-async-storage/async-storage';

import { LEGAL_DOCUMENT_VERSION } from '@/src/features/legal/constants/legalDocuments';

import type { SignupAgreements, SignupData } from '../types/auth';

const AUTH_SESSION_KEY = 'omeong-gameong.auth-session';
const USER_PROFILE_KEY = 'omeong-gameong.user-profile';
const CONSENT_KEY = 'omeong-gameong.consent-record';

export type AuthSession = {
  email: string;
  nickname: string;
  signedInAt: string;
};

type SavedUserProfile = Omit<SignupData, 'account'> & {
  account: Pick<SignupData['account'], 'email' | 'nickname'>;
};

/**
 * 동의 이력. 어떤 항목에 언제 어느 버전으로 동의했는지 남긴다.
 * 나중에 동의 여부로 다툼이 생기면 이 기록이 근거가 된다.
 *
 * TODO: 회원가입 API 연결 시 이 값을 서버로 보내고 동의 이력 테이블에 저장한다.
 *       기기에만 있는 기록은 앱을 지우면 사라지므로 증빙이 되지 못한다.
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

async function saveSession(email: string, nickname: string) {
  const session: AuthSession = {
    email,
    nickname,
    signedInAt: new Date().toISOString(),
  };

  await AsyncStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
  return session;
}

export async function getAuthSession() {
  const value = await AsyncStorage.getItem(AUTH_SESSION_KEY);
  return value ? (JSON.parse(value) as AuthSession) : null;
}

/** 추후 로그인 API 호출로 교체할 임시 저장 함수입니다. */
export async function signIn(email: string) {
  return saveSession(email, email.split('@')[0] || '여행자');
}

/**
 * 계정 정보와 선택 입력한 반려동물·여행 취향을 한 번에 저장합니다.
 * 실제 API 연결 전까지 비밀번호는 기기에 저장하지 않습니다.
 */
export async function completeSignup(data: SignupData) {
  const profile: SavedUserProfile = {
    agreements: data.agreements,
    account: {
      email: data.account.email,
      nickname: data.account.nickname,
    },
    pet: data.pet,
    travel: data.travel,
  };

  await AsyncStorage.setItem(USER_PROFILE_KEY, JSON.stringify(profile));
  await saveConsentRecord(data.agreements);
  return saveSession(data.account.email, data.account.nickname);
}

/**
 * 저장된 세션의 닉네임을 바꾼다.
 *
 * 마이페이지에서 닉네임을 수정하면 화면 상태만 바뀌고 세션은 회원가입 때 값을 그대로 들고 있어,
 * 앱을 다시 켰을 때 수정 전 이름으로 되돌아간다. 그것을 막기 위해 함께 갱신한다.
 * TODO: 사용자 API 연결 후에는 서버 응답을 정본으로 삼고 이 함수는 제거한다.
 */
export async function updateSessionNickname(nickname: string) {
  const session = await getAuthSession();
  if (!session) return null;

  const updated: AuthSession = { ...session, nickname };
  await AsyncStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(updated));
  return updated;
}

export async function signOut() {
  await AsyncStorage.removeItem(AUTH_SESSION_KEY);
}

/** 회원 탈퇴 시 기기에 남은 계정 관련 기록을 모두 지운다. */
export async function clearAccountStorage() {
  await AsyncStorage.multiRemove([AUTH_SESSION_KEY, USER_PROFILE_KEY, CONSENT_KEY]);
}

