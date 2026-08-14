import { useCallback, useState } from 'react';

import { MOCK_MEMOS } from '../mocks/memos.mock';
import type { TripMemo } from '../types/trip';

export type MemoDraft = {
  title: string;
  content: string;
};

/**
 * Day별 여행 메모 상태를 화면 단위로 관리한다.
 * TODO: 백엔드 준비 후 TanStack Query mutation 으로 교체
 */
export function useTripMemos() {
  const [memos, setMemos] = useState<TripMemo[]>(MOCK_MEMOS);

  const findMemoByScheduleId = useCallback(
    (scheduleId: string) => memos.find((memo) => memo.scheduleId === scheduleId) ?? null,
    [memos],
  );

  const saveMemo = useCallback((scheduleId: string, draft: MemoDraft) => {
    const trimmedTitle = draft.title.trim();
    const trimmedContent = draft.content.trim();

    setMemos((previous) => {
      const existing = previous.find((memo) => memo.scheduleId === scheduleId);

      if (trimmedTitle.length === 0 && trimmedContent.length === 0) {
        return previous.filter((memo) => memo.scheduleId !== scheduleId);
      }

      if (existing) {
        return previous.map((memo) =>
          memo.scheduleId === scheduleId
            ? { ...memo, title: trimmedTitle, content: trimmedContent }
            : memo,
        );
      }

      return [
        ...previous,
        {
          id: `memo-${scheduleId}-${Date.now()}`,
          scheduleId,
          title: trimmedTitle,
          content: trimmedContent,
        },
      ];
    });
  }, []);

  return { memos, findMemoByScheduleId, saveMemo };
}
