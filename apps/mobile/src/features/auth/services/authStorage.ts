import AsyncStorage from '@react-native-async-storage/async-storage';

import type { SignupData } from '../types/auth';

const AUTH_SESSION_KEY = 'omeong-gameong.auth-session';
const USER_PROFILE_KEY = 'omeong-gameong.user-profile';

export type AuthSession = {
  email: string;
  nickname: string;
  signedInAt: string;
};

type SavedUserProfile = Omit<SignupData, 'account'> & {
  account: Pick<SignupData['account'], 'email' | 'nickname'>;
};

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
    account: {
      email: data.account.email,
      nickname: data.account.nickname,
    },
    pet: data.pet,
    travel: data.travel,
  };

  await AsyncStorage.setItem(USER_PROFILE_KEY, JSON.stringify(profile));
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

