import { useCallback, useMemo, useState } from 'react';

import { useDebounce } from '@/src/hooks/useDebounce';
import type { DateRange, TravelLogListItem } from '@/src/types/travelLog';

import { formatDateRangeLabel } from '../utils/dateFormat';
import { filterTravelLogItems } from '../utils/filterTravelLogs';
import type { PetLogFilterOption } from '../utils/petFilterOptions';

const SEARCH_DEBOUNCE_MS = 300;

export function useTravelLogFilters(
  items: TravelLogListItem[],
  petOptions: PetLogFilterOption[],
) {
  const [searchInput, setSearchInput] = useState('');
  const [dateRange, setDateRange] = useState<DateRange | null>(null);
  const [selectedPetIds, setSelectedPetIds] = useState<string[]>([]);

  // 입력창은 즉시 반영하고, 실제 필터링에만 지연된 값을 사용한다.
  const debouncedSearch = useDebounce(searchInput, SEARCH_DEBOUNCE_MS);

  const filteredItems = useMemo(
    () =>
      filterTravelLogItems(items, {
        placeQuery: debouncedSearch,
        dateRange,
        petIds: selectedPetIds,
      }),
    [items, debouncedSearch, dateRange, selectedPetIds],
  );

  const isFilterActive =
    debouncedSearch.trim().length > 0 || dateRange !== null || selectedPetIds.length > 0;

  const dateChipLabel = dateRange ? formatDateRangeLabel(dateRange) : null;

  const petChipLabel = useMemo(() => {
    if (selectedPetIds.length === 0) {
      return null;
    }

    // 이름이 같아도 petId가 다르면 별개 항목이므로 라벨을 합치지 않는다.
    return petOptions
      .filter((option) => selectedPetIds.includes(option.petId))
      .map((option) => option.label)
      .join(' · ');
  }, [petOptions, selectedPetIds]);

  const clearDateFilter = useCallback(() => setDateRange(null), []);
  const clearPetFilter = useCallback(() => setSelectedPetIds([]), []);

  const resetFilters = useCallback(() => {
    setSearchInput('');
    setDateRange(null);
    setSelectedPetIds([]);
  }, []);

  return {
    searchInput,
    setSearchInput,
    dateRange,
    setDateRange,
    selectedPetIds,
    setSelectedPetIds,
    filteredItems,
    resultCount: filteredItems.length,
    isFilterActive,
    dateChipLabel,
    petChipLabel,
    clearDateFilter,
    clearPetFilter,
    resetFilters,
  };
}
