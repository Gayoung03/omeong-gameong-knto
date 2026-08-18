/**
 * 장소 도메인의 공통 값.
 *
 * 반려동물 동반 정책은 내 여행(trips)과 장소 탐색(places) 양쪽이 함께 쓰므로
 * 특정 기능 폴더가 아니라 여기에 둔다.
 */
export type PetPolicy = 'outdoorOnly' | 'indoorAllowed' | 'partialAllowed' | 'notAllowed';

const PET_POLICY_LABELS: Record<PetPolicy, string> = {
  outdoorOnly: '야외 · 목줄 필수',
  indoorAllowed: '실내 동반 가능',
  partialAllowed: '일부 구역 동반',
  notAllowed: '동반 불가',
};

export function getPetPolicyLabel(petPolicy: PetPolicy): string {
  return PET_POLICY_LABELS[petPolicy];
}
