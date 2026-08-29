import AsyncStorage from '@react-native-async-storage/async-storage';

import { deleteAccount } from '../api/authApi';

import { clearAccountStorage } from './authStorage';

/**
 * 회원 탈퇴 요청. local 계정은 비밀번호로 재확인한다(`DELETE /users/me`).
 *
 * 소셜 계정은 제공처 재인증(providerAccessToken)이 필요한데, 그 재인증 흐름(카카오
 * 재로그인 → 토큰 획득)은 아직 앱에 없다. 그래서 현재 이 함수는 **local 계정만** 다루고,
 * 소셜 계정은 화면에서 미리 걸러 "준비 중" 으로 안내한다(AccountWithdrawScreen).
 */
export async function withdrawAccount(password: string): Promise<void> {
  await deleteAccount(password);
}

/** 탈퇴 성공 후 기기에 남은 사용자 흔적(토큰·세션·동의기록·알림설정)을 지운다. */
export async function clearLocalUserData(): Promise<void> {
  try {
    await clearAccountStorage();
    await AsyncStorage.removeItem('notification-preferences');
  } catch {
    // 로컬 정리에 실패해도 탈퇴 자체는 완료된 상태이므로 흐름을 막지 않는다.
  }
}

/** 탈퇴 성공 시 다음 사용자가 이전 데이터를 보지 않도록 캐시를 비운다. */
export function shouldClearAppCacheOnWithdraw(): boolean {
  return true;
}
