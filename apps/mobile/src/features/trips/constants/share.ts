/**
 * 공유 링크의 기본 주소.
 *
 * 아직 실제로 존재하는 도메인이 아니라 자리를 잡아둔 값이다.
 * 배포 주소가 정해지면 이 값을 교체한다.
 * 같은 결정에 `constants/map.ts` 의 KAKAO_MAP_BASE_URL 도 함께 묶여 있다.
 *
 * TODO(팀 확인): 배포 도메인 확정
 */
const SHARE_BASE_URL = 'https://omeong-gameong.app';

export function buildTripShareUrl(tripId: string): string {
  return `${SHARE_BASE_URL}/trips/${tripId}`;
}
