/**
 * "방금 전" · "3시간 전" 처럼 지금으로부터 얼마나 지났는지.
 *
 * 알림 목록과 챗봇 대화 목록이 함께 쓴다. 두 곳이 같은 규칙을 따라야
 * "3시간 전"이 화면마다 다른 뜻이 되지 않는다.
 *
 * **날짜까지만 센다.** 하루가 넘어가면 "32일 전"이 되는데, 대화 목록에서는
 * 그 이상 정밀할 이유가 없다(정확한 날짜가 필요한 화면은 원본 문자열을 쓴다).
 * 미래 시각은 시계 차이로 생기는 것이라 "방금 전"으로 눌러 둔다.
 */
export function relativeTime(value: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return '방금 전';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}분 전`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}시간 전`;
  return `${Math.floor(seconds / 86400)}일 전`;
}
