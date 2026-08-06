import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import type {
  AddScheduleInput,
  PlaceCandidate,
  PlaceFilter,
  PlaceSourceTab,
  Schedule,
  ScheduleItem,
  Trip,
} from '../types/trip';
import { usePlaceCandidates, usePlaceSearchResults } from './usePlaceSearch';
import { tripQueryKeys } from './useTrips';

/** order 를 1부터 다시 매기고 마지막 항목의 이동 정보를 비운다 (useScheduleEdit 과 같은 규칙) */
function normalizeItems(items: ScheduleItem[]): ScheduleItem[] {
  return items.map((item, index) => ({
    ...item,
    order: index + 1,
    moveToNext: index === items.length - 1 ? null : item.moveToNext,
  }));
}

function appendItem(schedule: Schedule, input: AddScheduleInput): Schedule {
  const newItem: ScheduleItem = {
    // 같은 장소를 두 번 담을 수 있으므로 시각을 붙여 구분한다
    id: `${input.place.id}-item-${Date.now()}`,
    order: schedule.items.length + 1,
    place: input.place,
    isSaved: false,
    startTime: input.startTime,
    memo: input.memo,
    moveToNext: null,
  };

  return { ...schedule, items: normalizeItems([...schedule.items, newItem]) };
}

type UseAddScheduleParams = {
  tripId: string;
  schedules: Schedule[];
  /** 어느 날짜에 담을지. 일정 추가 버튼을 누른 날짜 */
  initialScheduleId: string;
};

/**
 * 일정 추가 화면의 상태와 담기 동작.
 *
 * 여행 데이터를 다 불러온 뒤에 마운트해야 한다 (초기값을 한 번만 읽기 때문).
 * TODO: 백엔드 준비 후 담기를 TanStack Query mutation 으로 교체.
 *       지금은 캐시에 직접 넣어 화면에서만 반영된다.
 */
export function useAddSchedule({ tripId, schedules, initialScheduleId }: UseAddScheduleParams) {
  const queryClient = useQueryClient();

  const [selectedScheduleId, setSelectedScheduleId] = useState(
    initialScheduleId || (schedules[0]?.id ?? ''),
  );
  const [activeTab, setActiveTab] = useState<PlaceSourceTab>('dayRecommend');
  const [filter, setFilter] = useState<PlaceFilter | null>(null);
  const [keywordInput, setKeywordInput] = useState('');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);
  /** 시간·메모 입력 시트를 띄울 대상 */
  const [pendingPlace, setPendingPlace] = useState<PlaceCandidate | null>(null);
  const [addedPlaceIds, setAddedPlaceIds] = useState<string[]>([]);

  const isSearching = searchKeyword.trim().length > 0;

  const candidatesQuery = usePlaceCandidates(activeTab, filter);
  const searchQuery = usePlaceSearchResults(searchKeyword, filter);

  const activeQuery = isSearching ? searchQuery : candidatesQuery;
  const places = useMemo(() => activeQuery.data ?? [], [activeQuery.data]);

  const selectedSchedule = useMemo(
    () => schedules.find((schedule) => schedule.id === selectedScheduleId) ?? schedules[0] ?? null,
    [schedules, selectedScheduleId],
  );

  const submitSearch = useCallback(() => {
    setSearchKeyword(keywordInput);
    setSelectedPlaceId(null);
  }, [keywordInput]);

  const clearSearch = useCallback(() => {
    setKeywordInput('');
    setSearchKeyword('');
    setSelectedPlaceId(null);
  }, []);

  const changeTab = useCallback((tab: PlaceSourceTab) => {
    setActiveTab(tab);
    setSelectedPlaceId(null);
  }, []);

  const changeFilter = useCallback((next: PlaceFilter) => {
    // 같은 칩을 다시 누르면 필터를 해제한다
    setFilter((previous) => (previous === next ? null : next));
    setSelectedPlaceId(null);
  }, []);

  const changeSchedule = useCallback((scheduleId: string) => {
    setSelectedScheduleId(scheduleId);
    setSelectedPlaceId(null);
  }, []);

  /** 캐시에 담긴 여행 정보를 갱신해 뒤로 갔을 때 바로 보이게 한다 */
  const addSchedule = useCallback(
    (input: AddScheduleInput) => {
      const applyToTrip = (trip: Trip | null | undefined): Trip | null | undefined => {
        if (!trip) {
          return trip;
        }

        return {
          ...trip,
          schedules: trip.schedules.map((schedule) =>
            schedule.id === input.scheduleId ? appendItem(schedule, input) : schedule,
          ),
        };
      };

      queryClient.setQueryData<Trip | null>(tripQueryKeys.latest(), applyToTrip);
      queryClient.setQueryData<Trip>(
        tripQueryKeys.detail(tripId),
        (trip) => applyToTrip(trip) ?? trip,
      );

      setAddedPlaceIds((previous) => [...previous, input.place.id]);
      setPendingPlace(null);
    },
    [queryClient, tripId],
  );

  return {
    // 목록
    places,
    isLoading: activeQuery.isLoading,
    isError: activeQuery.isError,
    refetch: activeQuery.refetch,

    // 검색
    keywordInput,
    setKeywordInput,
    isSearching,
    submitSearch,
    clearSearch,

    // 필터·탭·날짜
    filter,
    changeFilter,
    activeTab,
    changeTab,
    selectedSchedule,
    selectedScheduleId: selectedSchedule?.id ?? '',
    changeSchedule,

    // 선택
    selectedPlaceId,
    selectPlace: setSelectedPlaceId,
    pendingPlace,
    openAddSheet: setPendingPlace,
    closeAddSheet: () => setPendingPlace(null),

    // 담기
    addSchedule,
    addedPlaceIds,
  };
}
