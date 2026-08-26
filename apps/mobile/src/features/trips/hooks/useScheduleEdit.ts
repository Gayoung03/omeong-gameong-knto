import { useCallback, useMemo, useState } from 'react';

import type { Schedule, ScheduleItem } from '../types/trip';

/**
 * 순서가 바뀐 목록의 order 를 1부터 다시 매기고, 마지막 항목의 이동 정보를 비운다.
 *
 * 이동 거리·소요 시간은 실제 좌표 기반으로 서버가 계산해야 하는 값이라
 * 편집 화면에서는 재계산하지 않는다. 저장 시 서버가 다시 내려주는 것을 기준으로 삼는다.
 */
function normalizeItems(items: ScheduleItem[]): ScheduleItem[] {
  return items.map((item, index) => ({
    ...item,
    order: index + 1,
    moveToNext: index === items.length - 1 ? null : item.moveToNext,
  }));
}

function replaceSchedule(
  schedules: Schedule[],
  scheduleId: string,
  updateItems: (items: ScheduleItem[]) => ScheduleItem[],
): Schedule[] {
  return schedules.map((schedule) =>
    schedule.id === scheduleId
      ? { ...schedule, items: normalizeItems(updateItems(schedule.items)) }
      : schedule,
  );
}

/**
 * 일정 편집 화면의 임시 상태를 관리한다.
 * 저장을 누르기 전까지는 원본을 건드리지 않고 draft 만 수정한다.
 *
 * 여행 데이터를 다 불러온 뒤에 마운트해야 한다 (초기값을 한 번만 읽기 때문).
 * 저장은 `hooks/useSaveSchedule.ts` 가 맡고, 무엇이 바뀌었는지는
 * `api/scheduleSync.ts` 가 원본과 draft 를 비교해 알아낸다.
 */
export function useScheduleEdit(initialSchedules: Schedule[]) {
  const [draftSchedules, setDraftSchedules] = useState<Schedule[]>(initialSchedules);
  const [selectedScheduleId, setSelectedScheduleId] = useState<string>(
    initialSchedules[0]?.id ?? '',
  );

  const selectedSchedule = useMemo(
    () =>
      draftSchedules.find((schedule) => schedule.id === selectedScheduleId) ??
      draftSchedules[0] ??
      null,
    [draftSchedules, selectedScheduleId],
  );

  /**
   * 원본과 달라진 곳이 있는지.
   *
   * 순서·구성뿐 아니라 **시각과 메모까지 본다.** 항목이 제자리에 있어도
   * 시각만 고쳤으면 저장 버튼이 살아나야 한다.
   */
  const isDirty = useMemo(() => {
    return initialSchedules.some((original) => {
      const draft = draftSchedules.find((schedule) => schedule.id === original.id);

      if (!draft || draft.items.length !== original.items.length) {
        return true;
      }
      return draft.items.some((item, index) => {
        const before = original.items[index];
        return (
          item.id !== before.id || item.startTime !== before.startTime || item.memo !== before.memo
        );
      });
    });
  }, [draftSchedules, initialSchedules]);

  /** 드래그로 목록 순서를 바꿨을 때 */
  const reorderItems = useCallback((scheduleId: string, items: ScheduleItem[]) => {
    setDraftSchedules((previous) => replaceSchedule(previous, scheduleId, () => items));
  }, []);

  /** 방문 시각·메모만 고친다. 순서와 날짜는 건드리지 않는다. */
  const updateItemDetail = useCallback(
    (scheduleId: string, itemId: string, patch: { startTime: string | null; memo: string }) => {
      setDraftSchedules((previous) =>
        replaceSchedule(previous, scheduleId, (items) =>
          items.map((item) => (item.id === itemId ? { ...item, ...patch } : item)),
        ),
      );
    },
    [],
  );

  const removeItem = useCallback((scheduleId: string, itemId: string) => {
    setDraftSchedules((previous) =>
      replaceSchedule(previous, scheduleId, (items) => items.filter((item) => item.id !== itemId)),
    );
  }, []);

  /** 항목을 다른 날짜의 마지막 순서로 옮긴다 */
  const moveItemToSchedule = useCallback(
    (fromScheduleId: string, itemId: string, toScheduleId: string) => {
      if (fromScheduleId === toScheduleId) {
        return;
      }

      setDraftSchedules((previous) => {
        const movingItem = previous
          .find((schedule) => schedule.id === fromScheduleId)
          ?.items.find((item) => item.id === itemId);

        if (!movingItem) {
          return previous;
        }

        const removed = replaceSchedule(previous, fromScheduleId, (items) =>
          items.filter((item) => item.id !== itemId),
        );

        return replaceSchedule(removed, toScheduleId, (items) => [
          ...items,
          { ...movingItem, moveToNext: null },
        ]);
      });
    },
    [],
  );

  const reset = useCallback(() => {
    setDraftSchedules(initialSchedules);
  }, [initialSchedules]);

  return {
    draftSchedules,
    selectedSchedule,
    selectedScheduleId: selectedSchedule?.id ?? '',
    selectSchedule: setSelectedScheduleId,
    isDirty,
    reorderItems,
    updateItemDetail,
    removeItem,
    moveItemToSchedule,
    reset,
  };
}
