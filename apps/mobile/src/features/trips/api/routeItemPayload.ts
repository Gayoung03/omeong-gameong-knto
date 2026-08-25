import type { PlaceCategory } from '../types/trip';
import type { RouteItemCreateRequest, ServerScheduleItemType } from '../types/routeApi';

const ITEM_TYPE_BY_CATEGORY: Record<PlaceCategory, ServerScheduleItemType> = {
  accommodation: 'accommodation',
  attraction: 'attraction',
  cafe: 'cafe',
  etc: 'custom',
  restaurant: 'restaurant',
};

/**
 * 앱 분류 → 서버 `itemType`.
 *
 * **값이 정해진 쪽을 쓴다.** `place.category` 는 자유 문자열이 아니라 union 이라
 * 여기서 매핑이 끝난다. 모르는 값이 오면 `custom` 으로 떨어뜨린다.
 */
export function toServerItemType(category: PlaceCategory): ServerScheduleItemType {
  return ITEM_TYPE_BY_CATEGORY[category] ?? 'custom';
}

/**
 * 'YYYY-MM-DD' + 'HH:mm' → 서버가 받는 ISO 8601.
 *
 * **`+09:00` 을 반드시 붙인다.** 안 붙이면 서버가 UTC 로 해석해 아침 일정이
 * 전날로 밀린다. 어댑터가 응답에서 앞 10글자·11~16글자를 잘라 쓰는 것과 짝이다
 * (`api/routeAdapter.ts` 의 `toKstDate`·`toKstTime`).
 */
export function toKstIso(date: string, time: string): string {
  return `${date}T${time}:00+09:00`;
}

/**
 * 목록 맨 뒤에 담을 때 쓰는 순번.
 *
 * 서버가 `min(sortOrder, 현재 개수)` 로 자르므로 현재 개수보다 크기만 하면
 * "맨 뒤"가 된다. **앱은 그 날짜의 진짜 개수를 모른다** — 어댑터가 좌표 없는
 * 일정을 화면에서 걸러내는데 서버에는 남아 있기 때문이다(`api/scheduleSync.ts` 참고).
 * 그래서 개수를 세어 보내는 대신 "맨 뒤"라는 의도를 그대로 보낸다.
 */
export const APPEND_TO_END = 9_999;

type BuildParams = {
  category: PlaceCategory;
  placeId: string;
  /** 담을 날짜 'YYYY-MM-DD' */
  date: string;
  /** 'HH:mm'. 정하지 않았으면 null */
  startTime: string | null;
  memo: string;
  sortOrder?: number;
};

/** 일정 추가 요청 본문을 만든다. 담기와 편집 저장이 함께 쓴다. */
export function toRouteItemCreateRequest({
  category,
  placeId,
  date,
  startTime,
  memo,
  sortOrder = APPEND_TO_END,
}: BuildParams): RouteItemCreateRequest {
  return {
    itemType: toServerItemType(category),
    // 빈 문자열은 "안 썼다"와 구분되지 않아 아예 안 보낸다.
    note: memo.trim() || undefined,
    placeId,
    sortOrder,
    startsAt: startTime ? toKstIso(date, startTime) : undefined,
  };
}
