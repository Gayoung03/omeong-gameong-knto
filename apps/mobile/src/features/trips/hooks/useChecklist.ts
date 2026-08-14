import { useCallback, useMemo, useState } from 'react';

import { MOCK_CHECKLIST } from '../mocks/checklist.mock';
import type { ChecklistCategory, ChecklistItem } from '../types/trip';

const CATEGORY_ORDER: ChecklistCategory[] = ['pet', 'travel', 'etc'];

export type ChecklistSection = {
  category: ChecklistCategory;
  items: ChecklistItem[];
};

/**
 * 체크리스트 상태를 화면 단위로 관리한다.
 * TODO: 백엔드 준비 후 TanStack Query mutation 으로 교체
 */
export function useChecklist() {
  const [items, setItems] = useState<ChecklistItem[]>(MOCK_CHECKLIST);

  const sections = useMemo<ChecklistSection[]>(() => {
    return CATEGORY_ORDER.map((category) => ({
      category,
      items: items.filter((item) => item.category === category),
    })).filter((section) => section.items.length > 0);
  }, [items]);

  const checkedCount = useMemo(() => items.filter((item) => item.isChecked).length, [items]);

  const progressRate = items.length === 0 ? 0 : checkedCount / items.length;

  const toggleItem = useCallback((itemId: string) => {
    setItems((previous) =>
      previous.map((item) => (item.id === itemId ? { ...item, isChecked: !item.isChecked } : item)),
    );
  }, []);

  const addItem = useCallback((label: string, category: ChecklistCategory = 'etc') => {
    const trimmedLabel = label.trim();

    if (trimmedLabel.length === 0) {
      return;
    }

    setItems((previous) => [
      ...previous,
      {
        id: `checklist-custom-${Date.now()}`,
        category,
        label: trimmedLabel,
        isChecked: false,
        isRecommended: false,
      },
    ]);
  }, []);

  const removeItem = useCallback((itemId: string) => {
    setItems((previous) => previous.filter((item) => item.id !== itemId));
  }, []);

  return {
    sections,
    totalCount: items.length,
    checkedCount,
    progressRate,
    toggleItem,
    addItem,
    removeItem,
  };
}
