import AsyncStorage from '@react-native-async-storage/async-storage';

import { getAuthSession } from '@/src/features/auth/services/authStorage';

const KEY_PREFIX = 'omeong-gameong.travel-log-guide';
/** 로그인 전에 본 기록이 담기는 자리. */
const GUEST_SCOPE = 'guest';

/**
 * 여행 기록 사용법 안내를 봤는지 기억한다.
 *
 * **계정에 물려 둔다**(`savedStorage.ts` 와 같은 방식). 기기 하나를 여럿이 쓸 때
 * 앞사람이 닫았다고 뒷사람이 안내를 못 보면 안 된다.
 *
 * 서버에 두지 않는 이유는 이것이 **그 기기에서 봤는가**에 가까운 값이기 때문이다.
 * 기록 자체와 달리 잃어버려도 안내를 한 번 더 보는 것이 전부다.
 */
export type TravelLogGuideState = {
  /** 한 번이라도 띄운 적이 있다. 지금은 기록용이고 노출 여부를 정하지 않는다. */
  seen?: boolean;
  /**
   * 사용자가 "다시 보지 않기" 를 골랐다. **자동 노출을 끄는 유일한 스위치다.**
   * 껐어도 헤더의 도움말 버튼으로는 언제든 열린다.
   */
  hidden?: boolean;
};

async function scopedKey() {
  const session = await getAuthSession();
  return `${KEY_PREFIX}.${session?.email ?? GUEST_SCOPE}`;
}

export async function readTravelLogGuideState(): Promise<TravelLogGuideState> {
  try {
    const raw = await AsyncStorage.getItem(await scopedKey());
    if (!raw) return {};

    const parsed: unknown = JSON.parse(raw);
    // 저장된 값이 깨졌을 때 안내가 안 뜨는 것보다 한 번 더 뜨는 편이 낫다.
    return parsed && typeof parsed === 'object' ? (parsed as TravelLogGuideState) : {};
  } catch {
    return {};
  }
}

export async function writeTravelLogGuideState(state: TravelLogGuideState): Promise<void> {
  try {
    await AsyncStorage.setItem(await scopedKey(), JSON.stringify(state));
  } catch {
    // 저장에 실패해도 화면은 그대로 진행한다 — 다음에 안내가 한 번 더 뜰 뿐이다.
  }
}
