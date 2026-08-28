/**
 * 장소 도메인의 공통 값.
 * 내 여행(trips)과 장소 탐색(places) 양쪽이 함께 쓰므로 특정 기능 폴더가 아니라 여기에 둔다.
 */

/**
 * 반려동물 동반 정책. **5종이다.**
 *
 * 서버 `petPolicy.policyType` 과 1:1 대응한다 (2026-08-18 확정, `docs/api/places.md`).
 * 서버 표기는 snake_case(`outdoor_only`)라 연동 시 변환이 필요하다.
 *
 * `unknown` 은 "동반은 되지만 실내·야외 세부가 확인되지 않은 장소"다. 수집 대상 자체가
 * 동반 가능한 곳이라 '정보 없음'은 사실과 다르게 읽힌다(2026-08-28 확정).
 * 배지를 안 그리면 카드 높이가 들쭉날쭉해져서, 회색 배지로 세부만 미확인임을 알린다.
 */
export type PetPolicy =
  'outdoorOnly' | 'indoorAllowed' | 'partialAllowed' | 'notAllowed' | 'unknown';

const PET_POLICY_LABELS: Record<PetPolicy, string> = {
  outdoorOnly: '야외 · 목줄 필수',
  indoorAllowed: '실내 동반 가능',
  partialAllowed: '일부 구역 동반',
  notAllowed: '동반 불가',
  unknown: '동반 가능 · 세부 미확인',
};

export function getPetPolicyLabel(petPolicy: PetPolicy): string {
  return PET_POLICY_LABELS[petPolicy];
}

/** 서버 `petPolicy.policyType` 표기. DB enum 이라 snake_case 다. */
export type ServerPetPolicy =
  | 'indoor_allowed'
  | 'outdoor_only'
  | 'partial_allowed'
  | 'not_allowed'
  | 'unknown';

const PET_POLICY_BY_SERVER_VALUE: Record<ServerPetPolicy, PetPolicy> = {
  indoor_allowed: 'indoorAllowed',
  not_allowed: 'notAllowed',
  outdoor_only: 'outdoorOnly',
  partial_allowed: 'partialAllowed',
  unknown: 'unknown',
};

/**
 * 서버 표기 → 앱 표기.
 *
 * 장소 탐색과 내 여행이 같은 변환을 쓴다. 각자 두면 한쪽만 값이 늘었을 때
 * 다른 쪽이 조용히 `undefined` 를 그린다.
 */
export function toPetPolicy(serverValue: ServerPetPolicy): PetPolicy {
  return PET_POLICY_BY_SERVER_VALUE[serverValue] ?? 'unknown';
}
