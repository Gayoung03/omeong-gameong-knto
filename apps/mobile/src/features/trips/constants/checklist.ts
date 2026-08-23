import type { ChecklistCategory } from '../types/trip';

/**
 * 체크리스트 분류 이름표.
 *
 * 목데이터 파일에 있던 것을 옮겼다 — 서버 연결 후에도 계속 쓰는 값이라
 * 언젠가 지울 mock 파일에 두면 안 된다.
 *
 * 서버 `category` 는 `String(30)` 자유 문자열이고 앱은 이 세 가지를 쓴다
 * (docs/api/routes.md 체크리스트 절).
 */
export const CHECKLIST_CATEGORY_LABELS: Record<ChecklistCategory, string> = {
  pet: '🐾 반려동물 용품',
  travel: '🧳 여행 용품',
  etc: '📌 기타',
};

export const CHECKLIST_CATEGORY_ORDER: ChecklistCategory[] = ['pet', 'travel', 'etc'];

/** 서버가 준 자유 문자열을 앱이 아는 세 가지로 좁힌다. 모르는 값은 기타로 둔다. */
export function toChecklistCategory(serverCategory: string): ChecklistCategory {
  return serverCategory === 'pet' || serverCategory === 'travel' ? serverCategory : 'etc';
}
