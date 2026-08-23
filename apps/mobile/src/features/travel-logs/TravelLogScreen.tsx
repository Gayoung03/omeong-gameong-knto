import { useMemo, useRef } from 'react';
import { FlatList, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorState } from '@/src/components/feedback/ErrorState';
import { useAllPets } from '@/src/features/profile/hooks/usePets';
import { colors, spacing, typography } from '@/src/theme';
import type { TravelLogListItem } from '@/src/types/travelLog';

import { ActiveFilterChips } from './components/ActiveFilterChips';
import { DateFilterBottomSheet, type FilterSheetHandle } from './components/DateFilterBottomSheet';
import { PetFilterBottomSheet } from './components/PetFilterBottomSheet';
import { TravelLogFilterBar } from './components/TravelLogFilterBar';
import { TravelLogHeader } from './components/TravelLogHeader';
import { TravelLogSkeleton } from './components/TravelLogSkeleton';
import { TravelLogEmptyState, TravelLogNoResultsState } from './components/TravelLogStates';
import { TripCard } from './components/TripCard';
import { UngroupedLogCard } from './components/UngroupedLogCard';
import { useTravelLogFilters } from './hooks/useTravelLogFilters';
import { useTravelLogItems } from './hooks/useTravelLogItems';
import { buildPetFilterOptions, collectCompanions } from './utils/petFilterOptions';

export function TravelLogScreen() {
  const { data, isPending, isError, refetch } = useTravelLogItems();
  const { data: allPets = [] } = useAllPets();
  const dateSheetRef = useRef<FilterSheetHandle>(null);
  const petSheetRef = useRef<FilterSheetHandle>(null);

  const items = useMemo(() => data ?? [], [data]);

  // 필터 옵션의 1순위 출처는 전체 Pet 데이터이고, 기록 스냅샷은 그 뒤를 메운다.
  const petOptions = useMemo(() => {
    const trips = items.flatMap((item) => (item.kind === 'trip' ? [item.trip] : []));
    return buildPetFilterOptions(allPets, collectCompanions(trips));
  }, [allPets, items]);

  const {
    searchInput,
    setSearchInput,
    dateRange,
    setDateRange,
    selectedPetIds,
    setSelectedPetIds,
    filteredItems,
    resultCount,
    isFilterActive,
    dateChipLabel,
    petChipLabel,
    clearDateFilter,
    clearPetFilter,
    resetFilters,
  } = useTravelLogFilters(items, petOptions);

  const showResultCount = isFilterActive && !isPending && !isError;

  const renderItem = ({ item }: { item: TravelLogListItem }) =>
    item.kind === 'trip' ? (
      <TripCard trip={item.trip} />
    ) : (
      <UngroupedLogCard group={item.group} />
    );

  const renderEmptyContent = () => {
    if (isPending) {
      return <TravelLogSkeleton />;
    }

    if (isError) {
      return <ErrorState onRetry={() => refetch()} />;
    }

    if (isFilterActive) {
      return <TravelLogNoResultsState onResetFilters={resetFilters} />;
    }

    return <TravelLogEmptyState />;
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <FlatList
        contentContainerStyle={styles.content}
        data={isPending || isError ? [] : filteredItems}
        keyboardDismissMode="on-drag"
        keyboardShouldPersistTaps="handled"
        keyExtractor={(item) => (item.kind === 'trip' ? item.trip.tripId : item.group.groupId)}
        ListEmptyComponent={renderEmptyContent()}
        ListHeaderComponent={
          <View style={styles.header}>
            <TravelLogHeader />
            <TravelLogFilterBar
              isDateFilterActive={dateRange !== null}
              isPetFilterActive={selectedPetIds.length > 0}
              onChangeSearch={setSearchInput}
              onOpenDateFilter={() => dateSheetRef.current?.open()}
              onOpenPetFilter={() => petSheetRef.current?.open()}
              searchInput={searchInput}
              showPetFilter={petOptions.length >= 2}
            />
            <ActiveFilterChips
              dateChipLabel={dateChipLabel}
              onRemoveDateFilter={clearDateFilter}
              onRemovePetFilter={clearPetFilter}
              petChipLabel={petChipLabel}
            />
            {showResultCount ? (
              <Text style={styles.resultCount}>조건에 맞는 여행 {resultCount}개</Text>
            ) : null}
          </View>
        }
        renderItem={renderItem}
        showsVerticalScrollIndicator={false}
      />

      <DateFilterBottomSheet onApply={setDateRange} ref={dateSheetRef} value={dateRange} />

      <PetFilterBottomSheet
        onApply={setSelectedPetIds}
        options={petOptions}
        ref={petSheetRef}
        value={selectedPetIds}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: spacing.md,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  header: {
    gap: spacing.md,
  },
  resultCount: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
});
