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
 * `unknown` 은 "정책 정보가 아직 없는 장소"다. 배지를 안 그리면 카드 높이가 들쭉날쭉해지고
 * 정보가 없다는 사실 자체를 사용자가 알 수 없어, 회색 '정보 없음' 배지로 표시한다.
 */
export type PetPolicy =
  'outdoorOnly' | 'indoorAllowed' | 'partialAllowed' | 'notAllowed' | 'unknown';

const PET_POLICY_LABELS: Record<PetPolicy, string> = {
  outdoorOnly: '야외 · 목줄 필수',
  indoorAllowed: '실내 동반 가능',
  partialAllowed: '일부 구역 동반',
  notAllowed: '동반 불가',
  unknown: '정보 없음',
};

export function getPetPolicyLabel(petPolicy: PetPolicy): string {
  return PET_POLICY_LABELS[petPolicy];
}
