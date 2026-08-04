/**
 * 공유 링크의 기본 주소.
 * TODO: 웹 페이지·도메인이 정해지면 이 값만 교체한다. (팀 확인 필요)
 */
const SHARE_BASE_URL = 'https://omeong-gameong.app';

export function buildTripShareUrl(tripId: string): string {
  return `${SHARE_BASE_URL}/trips/${tripId}`;
}
