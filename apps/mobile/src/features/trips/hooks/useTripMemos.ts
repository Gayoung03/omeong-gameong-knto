import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';

import {
  createTripMemo,
  getTripMemos,
  removeTripMemo,
  updateTripMemo,
} from '../api/memosApi';

import { tripQueryKeys } from './useTrips';

export type MemoDraft = {
  title: string;
  content: string;
};

export const memosQueryKey = (tripId: string) =>
  [...tripQueryKeys.detail(tripId), 'memos'] as const;

/**
 * Day 별 여행 메모.
 *
 * 화면은 "이 Day 의 메모"를 하나만 다룬다. 서버는 한 Day 에 여러 개를 허용하지만
 * 화면이 하나만 보여주므로 **가장 먼저 쓴 메모를 그 Day 의 메모로 삼는다.**
 *
 * 저장은 세 갈래다 — 없으면 만들고, 있으면 고치고, **내용을 비우면 지운다.**
 * 서버는 `content` 를 필수로 받는다(제목만 있는 메모는 만들 수 없다).
 * 빈 메모를 남겨두면 목록에 빈 카드가 생기기도 한다.
 */
export function useTripMemos(tripId: string) {
  const queryClient = useQueryClient();
  const queryKey = memosQueryKey(tripId);

  const { data: memos = [] } = useQuery({
    queryFn: () => getTripMemos(tripId),
    queryKey,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const findMemoByScheduleId = useCallback(
    (scheduleId: string) => memos.find((memo) => memo.scheduleId === scheduleId) ?? null,
    [memos],
  );

  const saveMutation = useMutation({
    mutationFn: async ({ draft, scheduleId }: { scheduleId: string; draft: MemoDraft }) => {
      const title = draft.title.trim();
      const content = draft.content.trim();
      const existing = memos.find((memo) => memo.scheduleId === scheduleId) ?? null;

      if (content.length === 0) {
        if (existing) await removeTripMemo(existing.id);
        return;
      }

      if (existing) {
        await updateTripMemo(existing.id, { content, title });
        return;
      }

      await createTripMemo(tripId, { content, scheduleId, title });
    },
    onSuccess: invalidate,
  });

  const saveMemo = useCallback(
    (scheduleId: string, draft: MemoDraft) => saveMutation.mutate({ draft, scheduleId }),
    [saveMutation],
  );

  return { memos, findMemoByScheduleId, saveMemo };
}
