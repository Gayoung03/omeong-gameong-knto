import { useMutation, useQueryClient } from '@tanstack/react-query';

import { saveScheduleChanges } from '../api/scheduleSync';
import type { Schedule } from '../types/trip';

import { tripQueryKeys } from './useTrips';

/**
 * 일정 편집 저장.
 *
 * 원본과 draft 를 함께 넘긴다 — 무엇이 바뀌었는지는
 * `api/scheduleSync.ts` 가 두 목록을 비교해 알아낸다.
 *
 * 저장이 끝나면 이 여행의 캐시를 버린다. 서버가 순번을 다시 매기므로
 * 화면이 들고 있던 값과 어긋날 수 있다.
 */
export function useSaveSchedule(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ draft, original }: { original: Schedule[]; draft: Schedule[] }) =>
      saveScheduleChanges(tripId, original, draft),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tripQueryKeys.detail(tripId) });
      queryClient.invalidateQueries({ queryKey: tripQueryKeys.list() });
    },
  });
}
