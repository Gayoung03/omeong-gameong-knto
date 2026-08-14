/**
 * 로컬 목업용 고유 ID 생성기.
 * 이름 등 사용자 입력은 절대 섞지 않는다. 같은 이름으로 다시 등록해도
 * 항상 새 개체가 되어야 하고, 과거 기록이 참조하는 ID와 충돌해서도 안 되기 때문이다.
 * TODO: 실제 API 연동 시 서버가 발급한 ID로 대체
 */
export function createId(prefix: string): string {
  const random = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${Date.now().toString(36)}-${random}`;
}
