import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

import {
  addChecklistItem,
  getChecklistItems,
  removeChecklistItem,
  updateChecklistItem,
} from '../api/checklistApi';
import { CHECKLIST_CATEGORY_ORDER } from '../constants/checklist';
import type { ChecklistCategory, ChecklistItem } from '../types/trip';

import { tripQueryKeys } from './useTrips';

export type ChecklistSection = {
  category: ChecklistCategory;
  items: ChecklistItem[];
};

type ToggleVariables = {
  itemId: string;
  isChecked: boolean;
};

/**
 * 낙관적 갱신 전에 찍어둔 목록. 실패하면 이걸로 되돌린다.
 *
 * 제네릭으로 명시하는 이유 — 키를 알파벳순으로 쓰다 보니 `onError` 가 `onMutate`
 * 보다 위에 오는데, 그러면 TanStack Query 가 context 타입을 추론하지 못한다.
 */
type ToggleContext = {
  previous: ChecklistItem[] | undefined;
};

export const checklistQueryKey = (tripId: string) =>
  [...tripQueryKeys.detail(tripId), 'checklist'] as const;

/**
 * 여행 준비 체크리스트.
 *
 * 예전에는 목데이터를 화면 상태로만 들고 있어서 탭을 나가면 사라졌다.
 * 이제 서버가 정본이다 — 체크 하나를 눌러도 바로 저장된다.
 *
 * **낙관적 갱신을 쓴다.** 체크박스는 누르는 즉시 반응해야 하는데 왕복을 기다리면
 * 한 박자 늦게 움직인다. 먼저 화면을 바꾸고, 실패하면 되돌린다.
 */
export function useChecklist(tripId: string) {
  const queryClient = useQueryClient();
  const queryKey = checklistQueryKey(tripId);

  const { data: items = [] } = useQuery({
    queryFn: () => getChecklistItems(tripId),
    queryKey,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const toggleMutation = useMutation<ChecklistItem, Error, ToggleVariables, ToggleContext>({
    mutationFn: ({ isChecked, itemId }) => updateChecklistItem(itemId, { isChecked }),
    onError: (_error, _variables, context) => {
      // 되돌린다. context 는 아래 onMutate 가 남긴 직전 목록이다.
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous);
      }
    },
    onMutate: async ({ isChecked, itemId }) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<ChecklistItem[]>(queryKey);

      queryClient.setQueryData<ChecklistItem[]>(queryKey, (current = []) =>
        current.map((item) => (item.id === itemId ? { ...item, isChecked } : item)),
      );

      return { previous };
    },
    onSettled: invalidate,
  });

  const addMutation = useMutation({
    mutationFn: ({ category, label }: { label: string; category: ChecklistCategory }) =>
      addChecklistItem(tripId, { category, label, sortOrder: items.length }),
    onSuccess: invalidate,
  });

  const removeMutation = useMutation({
    mutationFn: (itemId: string) => removeChecklistItem(itemId),
    onSuccess: invalidate,
  });

  const sections = useMemo<ChecklistSection[]>(
    () =>
      CHECKLIST_CATEGORY_ORDER.map((category) => ({
        category,
        items: items.filter((item) => item.category === category),
      })).filter((section) => section.items.length > 0),
    [items],
  );

  const checkedCount = useMemo(() => items.filter((item) => item.isChecked).length, [items]);

  const toggleItem = useCallback(
    (itemId: string) => {
      const target = items.find((item) => item.id === itemId);
      if (!target) return;
      toggleMutation.mutate({ isChecked: !target.isChecked, itemId });
    },
    [items, toggleMutation],
  );

  const addItem = useCallback(
    (label: string, category: ChecklistCategory = 'etc') => {
      const trimmedLabel = label.trim();
      if (trimmedLabel.length === 0) return;
      addMutation.mutate({ category, label: trimmedLabel });
    },
    [addMutation],
  );

  const removeItem = useCallback(
    (itemId: string) => removeMutation.mutate(itemId),
    [removeMutation],
  );

  return {
    sections,
    totalCount: items.length,
    checkedCount,
    progressRate: items.length === 0 ? 0 : checkedCount / items.length,
    toggleItem,
    addItem,
    removeItem,
  };
}
