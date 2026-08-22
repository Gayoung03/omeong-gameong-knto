import AsyncStorage from '@react-native-async-storage/async-storage';

import { clearAccountStorage } from './authStorage';

const WITHDRAW_DELAY_MS = 600;

/**
 * 아직 실제 탈퇴 API가 없다. 계정이 남아있는데 기기 데이터만 지워지면
 * 화면 확인이 불가능해지므로, 목업 동안에는 로컬 정리를 실행하지 않는다.
 * TODO: 실제 API 연결 시 false로 바꾼다.
 */
const IS_WITHDRAW_MOCKED = true;

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

/**
 * 회원 탈퇴 요청. 지금은 화면 흐름만 확인할 수 있는 목업이라 실제로 지우는 데이터가 없다.
 *
 * TODO: 실제 API 연결 (DELETE /users/me). 호출 전에 본인 확인 또는 최근 로그인 상태 확인이 필요하다.
 * TODO: 소셜 로그인 사용자는 제공자 재인증(reauthenticate) 후에 호출해야 한다.
 * TODO(server): 탈퇴 계정 식별값 보관 방식과 동일 이메일 재가입 차단 정책을 서버에서 적용해야 한다.
 *               보관 기간은 개인정보 처리방침과 함께 확정한다. (클라이언트는 차단 목록을 갖지 않는다)
 */
export async function withdrawAccount(): Promise<void> {
  await wait(WITHDRAW_DELAY_MS);
}

/**
 * 탈퇴 성공 후 기기에 남은 사용자 흔적을 지운다.
 *
 * TODO: 인증 토큰 삭제(expo-secure-store) — 아직 토큰을 저장하는 코드가 없어 비워 둔다.
 * TODO: 세션 동안만 유지되는 zustand 스토어(useSavedLogStore, useLogDraftStore)도 초기화한다.
 */
export async function clearLocalUserData(): Promise<void> {
  if (IS_WITHDRAW_MOCKED) return;

  try {
    await clearAccountStorage();
    await AsyncStorage.removeItem('notification-preferences');
  } catch {
    // 로컬 정리에 실패해도 탈퇴 자체는 완료된 상태이므로 흐름을 막지 않는다.
  }
}

/** 목업 동안에는 캐시를 비우지 않아 화면 데이터가 그대로 남는다. */
export function shouldClearAppCacheOnWithdraw(): boolean {
  return !IS_WITHDRAW_MOCKED;
}
