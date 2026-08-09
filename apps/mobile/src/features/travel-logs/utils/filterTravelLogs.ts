import type { DateRange, TravelLogFilters, TravelLogListItem, Trip } from '@/src/types/travelLog';

import { getGroupMonthRange } from './dateFormat';

/** 장소명 부분 일치 (대소문자 무시) */
export function matchesPlaceName(trip: Trip, query: string): boolean {
  const normalized = query.trim().toLowerCase();

  if (normalized.length === 0) {
    return true;
  }

  return trip.placeName.toLowerCase().includes(normalized);
}

/**
 * 날짜 기준: 여행 기간과 선택 기간의 "겹침(overlap)".
 * 로그 단위 timestamp 모델이 없으므로 여행 시작일/종료일을 기준으로 삼는다.
 * 완전 포함이 아니라 겹침이므로, 선택 기간에 일부만 걸친 여행도 노출된다.
 */
export function matchesDateRange(target: DateRange, filter: DateRange | null): boolean {
  if (!filter) {
    return true;
  }

  return target.start <= filter.end && target.end >= filter.start;
}

/**
 * 선택된 반려동물 중 한 마리라도 함께한 여행이면 통과.
 * 비교 기준은 언제나 petId다. 이름이 같아도 다른 개체면 걸러지고,
 * 프로필을 지운 반려동물의 과거 여행도 그대로 매칭된다.
 */
export function matchesPetIds(trip: Trip, petIds: string[]): boolean {
  if (petIds.length === 0) {
    return true;
  }

  return trip.companions.some((companion) => petIds.includes(companion.petId));
}

/** 장소·날짜·반려동물 조건을 AND로 결합해 목록을 좁힌다. */
export function filterTravelLogItems(
  items: TravelLogListItem[],
  filters: TravelLogFilters,
): TravelLogListItem[] {
  const hasPlaceQuery = filters.placeQuery.trim().length > 0;
  const hasPetFilter = filters.petIds.length > 0;

  return items.filter((item) => {
    if (item.kind === 'ungrouped') {
      // 미연결 기록 그룹은 장소명·반려동물 정보를 갖지 않으므로
      // 두 필터가 활성화되면 구조적으로 매칭될 수 없어 숨긴다.
      if (hasPlaceQuery || hasPetFilter) {
        return false;
      }

      return matchesDateRange(getGroupMonthRange(item.group), filters.dateRange);
    }

    const { trip } = item;

    return (
      matchesPlaceName(trip, filters.placeQuery) &&
      matchesDateRange({ start: trip.startDate, end: trip.endDate }, filters.dateRange) &&
      matchesPetIds(trip, filters.petIds)
    );
  });
}
