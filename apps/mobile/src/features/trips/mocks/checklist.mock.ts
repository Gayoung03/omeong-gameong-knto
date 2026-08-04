import type { ChecklistCategory, ChecklistItem } from '../types/trip';

type ChecklistSeed = {
  label: string;
  isChecked?: boolean;
};

function createItems(category: ChecklistCategory, seeds: ChecklistSeed[]): ChecklistItem[] {
  return seeds.map((seed, index) => ({
    id: `checklist-${category}-${index + 1}`,
    category,
    label: seed.label,
    isChecked: seed.isChecked ?? false,
    isRecommended: true,
  }));
}

/** 반려동물 동반 여행 기본 추천 체크리스트 */
export const MOCK_CHECKLIST: ChecklistItem[] = [
  ...createItems('pet', [
    { label: '목줄 · 가슴줄 · 리드줄', isChecked: true },
    { label: '이동가방 (켄넬)', isChecked: true },
    { label: '배변패드 · 비닐봉투', isChecked: true },
    { label: '휴대용 식기세트' },
    { label: '간식 · 사료', isChecked: true },
    { label: '예방접종 수첩' },
    { label: '해충 퇴치제' },
    { label: '담요 · 장난감', isChecked: true },
    { label: '브러시 · 옷' },
    { label: '숙소용 방수 시트' },
    { label: '차량 안전벨트', isChecked: true },
    { label: '네임택' },
  ]),
  ...createItems('travel', [
    { label: '신분증 · 항공권', isChecked: true },
    { label: '충전기 · 보조배터리' },
    { label: '생수 · 간식' },
    { label: '상비약' },
    { label: '자외선 차단제' },
  ]),
];

export const CHECKLIST_CATEGORY_LABELS: Record<ChecklistCategory, string> = {
  pet: '🐾 반려동물 용품',
  travel: '🧳 여행 용품',
  etc: '📌 기타',
};
