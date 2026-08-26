import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState } from 'react';

import { getApiErrorDetail, getApiErrorMessage } from '@/src/services/apiError';

import { toRouteItemCreateRequest } from '../api/routeItemPayload';
import { addRouteItem } from '../api/tripsApi';
import type {
  AddScheduleInput,
  PlaceCandidate,
  PlaceFilter,
  PlaceSourceTab,
  Schedule,
} from '../types/trip';
import { toDaySearchArea, toStaySearchArea } from '../utils/placeSearchArea';
import { usePlaceCandidates, usePlaceSearchResults } from './usePlaceSearch';
import { tripQueryKeys } from './useTrips';

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
  const [addErrorMessage, setAddErrorMessage] = useState<string>();

  const isSearching = searchKeyword.trim().length > 0;

  const selectedSchedule = useMemo(
    () => schedules.find((schedule) => schedule.id === selectedScheduleId) ?? schedules[0] ?? null,
    [schedules, selectedScheduleId],
  );

  /** 탭마다 기준이 다르다. 추천은 그 날짜의 마지막 일정, 내 숙소는 담긴 숙소. */
  const searchArea = useMemo(() => {
    if (activeTab === 'dayRecommend') {
      return toDaySearchArea(selectedSchedule?.items ?? []);
    }

    if (activeTab === 'nearStay') {
      return toStaySearchArea(schedules);
    }

    return null;
  }, [activeTab, schedules, selectedSchedule]);

  const candidatesQuery = usePlaceCandidates(activeTab, filter, searchArea);
  const searchQuery = usePlaceSearchResults(searchKeyword, filter);

  const activeQuery = isSearching ? searchQuery : candidatesQuery;
  const places = useMemo(() => activeQuery.data ?? [], [activeQuery.data]);

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

  /**
   * 담기 — POST /route-days/{routeDayId}/items
   *
   * 예전에는 `queryClient.setQueryData` 로 캐시만 바꿨다. 화면에는 담긴 것처럼
   * 보였지만 **서버에는 아무것도 안 갔고, 앱을 껐다 켜면 사라졌다.**
   *
   * 성공하면 이 여행의 캐시를 버리고 다시 받는다 — 서버가 순번을 다시 매기고
   * 이동 정보(route_moves)까지 새로 이어서, 앱이 흉내 내면 어긋난다.
   */
  const addMutation = useMutation({
    mutationFn: (input: AddScheduleInput) => {
      const schedule = schedules.find((item) => item.id === input.scheduleId);
      if (!schedule) {
        throw new Error(`담을 날짜를 찾을 수 없습니다: ${input.scheduleId}`);
      }

      return addRouteItem(
        input.scheduleId,
        toRouteItemCreateRequest({
          category: input.place.category,
          date: schedule.date,
          memo: input.memo,
          placeId: input.place.id,
          startTime: input.startTime,
        }),
      );
    },
    onError: (error, input) => {
      // 낙관적으로 표시해둔 '담김'을 되돌린다. 안 그러면 실패했는데
      // 카드가 계속 '담김'으로 남아 사용자가 다시 담을 수 없다.
      setAddedPlaceIds((previous) => {
        const index = previous.lastIndexOf(input.place.id);
        if (index === -1) return previous;
        return [...previous.slice(0, index), ...previous.slice(index + 1)];
      });
      const detail = getApiErrorDetail(error);
      setAddErrorMessage(
        detail
          ? `${getApiErrorMessage(error).description} (${detail})`
          : getApiErrorMessage(error).description,
      );
    },
    onSuccess: () => {
      setAddErrorMessage(undefined);
      queryClient.invalidateQueries({ queryKey: tripQueryKeys.detail(tripId) });
      queryClient.invalidateQueries({ queryKey: tripQueryKeys.list() });
    },
  });

  const addSchedule = useCallback(
    (input: AddScheduleInput) => {
      // 왕복을 기다리면 시트가 한 박자 늦게 닫혀 눌린 건지 알 수 없다.
      // 먼저 닫고 표시한 뒤, 실패하면 onError 가 되돌린다.
      setPendingPlace(null);
      setAddedPlaceIds((previous) => [...previous, input.place.id]);
      addMutation.mutate(input);
    },
    [addMutation],
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
    isAdding: addMutation.isPending,
    addErrorMessage,
  };
}
