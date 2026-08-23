import type { PlaceCategory, Schedule } from '../types/trip';
import type { ServerScheduleItemType } from '../types/routeApi';

import { addRouteItem, getTripRaw, removeRouteItem, reorderRouteItems } from './tripsApi';

/**
 * 편집 화면의 변경분을 서버에 반영한다.
 *
 * 편집 화면은 저장을 누를 때까지 draft 만 고친다. 그래서 여기서 **원본과 draft 를
 * 비교해** 무엇이 바뀌었는지 알아내고, 필요한 호출만 보낸다.
 *
 * 화면이 할 수 있는 일은 세 가지다 — 순서 바꾸기, 지우기, 다른 날짜로 옮기기.
 */

const ITEM_TYPE_BY_CATEGORY: Record<PlaceCategory, ServerScheduleItemType> = {
  accommodation: 'accommodation',
  attraction: 'attraction',
  cafe: 'cafe',
  etc: 'custom',
  restaurant: 'restaurant',
};

/** 항목 id → 그 항목이 속한 날짜 id */
function dayOfItem(schedules: Schedule[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const schedule of schedules) {
    for (const item of schedule.items) {
      map.set(item.id, schedule.id);
    }
  }
  return map;
}

export async function saveScheduleChanges(
  tripId: string,
  original: Schedule[],
  draft: Schedule[],
): Promise<void> {
  const originalDay = dayOfItem(original);
  const draftDay = dayOfItem(draft);

  const removedIds = [...originalDay.keys()].filter((id) => !draftDay.has(id));
  // 서버에 "일정을 다른 날짜로 옮기는" API 가 없다. PATCH 는 시각·메모만 고친다.
  // 그래서 지웠다가 새 날짜에 다시 만든다.
  // 이때 추천 점수·추천 이유는 따라가지 못한다 — 사용자가 직접 옮긴 일정이라
  // 원래의 추천 근거가 더는 맞지 않기도 해서, 지금은 이 손실을 받아들인다.
  const movedIds = [...draftDay.keys()].filter(
    (id) => originalDay.has(id) && originalDay.get(id) !== draftDay.get(id),
  );

  for (const itemId of [...removedIds, ...movedIds]) {
    await removeRouteItem(itemId);
  }

  // 옮긴 항목은 새로 만들어지므로 서버 id 가 바뀐다. 순서를 보낼 때 쓰려고 적어둔다.
  const serverIdOf = new Map<string, string>();
  const movedIdSet = new Set(movedIds);

  for (const schedule of draft) {
    for (const [index, item] of schedule.items.entries()) {
      if (!movedIdSet.has(item.id)) continue;

      const created = await addRouteItem(schedule.id, {
        itemType: ITEM_TYPE_BY_CATEGORY[item.place.category] ?? 'custom',
        note: item.memo || undefined,
        placeId: item.place.id,
        sortOrder: index,
      });
      serverIdOf.set(item.id, created.id);
    }
  }

  await reorderChangedDays(tripId, original, draft, serverIdOf);
}

/**
 * 날짜별 순서를 확정한다.
 *
 * **걸러진 일정까지 챙겨야 한다.** 어댑터는 좌표가 없는 일정(직접 입력)을 화면에서
 * 빼는데, 서버에는 그대로 남아 있다. 순서 API 는 그 날짜의 항목 전체를 요구하므로
 * 화면이 아는 것만 보내면 422 로 거절당한다.
 *
 * 그래서 서버 상태를 다시 읽어 빠진 항목을 **뒤에 붙인다.** 사용자가 본 적 없는
 * 항목이라 자리를 지켜줄 근거가 없다. 화면에서 다룰 수 있게 되면 이 보정은 사라진다.
 */
async function reorderChangedDays(
  tripId: string,
  original: Schedule[],
  draft: Schedule[],
  serverIdOf: Map<string, string>,
): Promise<void> {
  const changedDays = draft.filter((schedule) => {
    const before = original.find((item) => item.id === schedule.id);
    if (!before) return true;
    if (before.items.length !== schedule.items.length) return true;
    return schedule.items.some((item, index) => item.id !== before.items[index].id);
  });

  if (changedDays.length === 0) return;

  const serverRoute = await getTripRaw(tripId);

  for (const schedule of changedDays) {
    const serverDay = serverRoute.routeDays.find((day) => day.id === schedule.id);
    if (!serverDay) continue;

    const orderedIds = schedule.items.map((item) => serverIdOf.get(item.id) ?? item.id);
    const known = new Set(orderedIds);
    const hidden = serverDay.items.map((item) => item.id).filter((id) => !known.has(id));

    if (hidden.length > 0 && __DEV__) {
      console.warn(
        `[trips] 화면에 없는 일정 ${hidden.length}건을 맨 뒤로 보냅니다 (day ${serverDay.dayNumber})`,
      );
    }

    const finalOrder = [...orderedIds, ...hidden];
    if (finalOrder.length === 0) continue;

    await reorderRouteItems(schedule.id, finalOrder);
  }
}
