import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useMemo, useRef } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { GestureDetector } from 'react-native-gesture-handler';
import Animated from 'react-native-reanimated';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { ErrorState } from '@/src/components/feedback/ErrorState';
import { colors, radius, spacing, typography } from '@/src/theme';

import { AddScheduleSheet } from '../components/AddScheduleSheet';
import { PlaceCandidateCard } from '../components/PlaceCandidateCard';
import { PlaceFilterChips } from '../components/PlaceFilterChips';
import { PlaceSearchBar } from '../components/PlaceSearchBar';
import { PlaceSourceTabs } from '../components/PlaceSourceTabs';
import { TripMapView, type TripMapViewHandle } from '../components/TripMapView';
import { MAX_MAP_CANDIDATES, PLACE_SOURCE_EMPTY_MESSAGES } from '../constants/placeSearch';
import { useAddSchedule } from '../hooks/useAddSchedule';
import { useDraggableSheet } from '../hooks/useDraggableSheet';
import { useTrip } from '../hooks/useTrips';
import type { PlaceCandidate, Trip } from '../types/trip';
import type { KakaoMapFitMode } from '../utils/kakaoMapHtml';

type AddScheduleScreenProps = {
  tripId: string;
  /** 일정 추가 버튼을 누른 날짜. 없으면 첫 번째 날 */
  scheduleId?: string;
};

const MAP_CONTROLS: {
  fitMode: KakaoMapFitMode;
  iconName: keyof typeof Ionicons.glyphMap;
  label: string;
}[] = [
  { fitMode: 'all', iconName: 'scan-outline', label: '전체 보기' },
  { fitMode: 'route', iconName: 'git-branch-outline', label: '이 날짜 루트 보기' },
];

/** 시트 높이 후보를 화면 높이 기준으로 잡는다 (지도 넓게 / 기본 / 목록 넓게) */
const SNAP_RATIOS = [0.28, 0.55, 0.86];

export function AddScheduleScreen({ tripId, scheduleId }: AddScheduleScreenProps) {
  const { data: trip, isLoading, isError, refetch } = useTrip(tripId);

  if (isLoading) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.stateDescription}>여행 정보를 불러오는 중이에요</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (isError || !trip) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <ErrorState onRetry={() => refetch()} />
      </SafeAreaView>
    );
  }

  // 여행 데이터를 다 받은 뒤에 마운트해야 useAddSchedule 이 초기값을 제대로 읽는다
  return <AddScheduleContent initialScheduleId={scheduleId ?? ''} trip={trip} />;
}

type AddScheduleContentProps = {
  trip: Trip;
  initialScheduleId: string;
};

function AddScheduleContent({ trip, initialScheduleId }: AddScheduleContentProps) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { height: windowHeight } = useWindowDimensions();
  const listRef = useRef<FlatList<PlaceCandidate>>(null);
  const mapRef = useRef<TripMapViewHandle>(null);

  const snapPoints = useMemo(
    () => SNAP_RATIOS.map((ratio) => Math.round(windowHeight * ratio)),
    [windowHeight],
  );
  const { gesture, sheetStyle, aboveSheetStyle } = useDraggableSheet({
    snapPoints,
    initialIndex: 1,
  });

  const {
    places,
    isLoading,
    isError,
    refetch,
    keywordInput,
    setKeywordInput,
    isSearching,
    submitSearch,
    clearSearch,
    filter,
    changeFilter,
    activeTab,
    changeTab,
    selectedSchedule,
    selectedScheduleId,
    selectedPlaceId,
    selectPlace,
    pendingPlace,
    openAddSheet,
    closeAddSheet,
    addSchedule,
    addedPlaceIds,
    addErrorMessage,
  } = useAddSchedule({ tripId: trip.id, schedules: trip.schedules, initialScheduleId });

  /**
   * 뒤로 갈 곳이 없으면(주소로 바로 들어왔거나 히스토리가 비었으면) 여행 상세로 보낸다.
   * 웹에서 `router.back()` 만 부르면 "GO_BACK was not handled by any navigator" 로 죽는다.
   */
  const goToTrip = () => {
    if (router.canGoBack()) {
      router.back();
      return;
    }
    router.replace({ params: { tripId: trip.id }, pathname: '/trips/[tripId]' });
  };

  const mapCandidates = places.slice(0, MAX_MAP_CANDIDATES);
  // 후보 목록이나 날짜가 바뀔 때만 지도를 새로 그린다
  const redrawKey = `${selectedScheduleId}|${mapCandidates.map((place) => place.id).join(',')}`;

  /** 마커를 누르면 목록에서도 해당 장소로 이동시킨다 */
  const handleSelectPlace = (placeId: string | null) => {
    selectPlace(placeId);

    if (!placeId) {
      return;
    }

    const index = places.findIndex((place) => place.id === placeId);

    if (index >= 0) {
      listRef.current?.scrollToIndex({ index, animated: true, viewPosition: 0.2 });
    }
  };

  return (
    <View style={styles.safeArea}>
      <View style={StyleSheet.absoluteFill}>
        <TripMapView
          candidates={mapCandidates}
          initialFitMode="candidates"
          initialSelectedPlaceId={null}
          items={selectedSchedule?.items ?? []}
          onSelectPlace={handleSelectPlace}
          redrawKey={redrawKey}
          ref={mapRef}
        />
      </View>

      <View pointerEvents="box-none" style={[styles.topOverlay, { paddingTop: insets.top }]}>
        <PlaceSearchBar
          isSearching={isSearching}
          onChangeValue={setKeywordInput}
          onClear={clearSearch}
          onPressBack={() => router.back()}
          onSubmit={submitSearch}
          value={keywordInput}
        />
        <PlaceFilterChips onSelect={changeFilter} value={filter} />
      </View>

      <Animated.View style={[styles.mapControls, aboveSheetStyle]}>
        {MAP_CONTROLS.map((control) => (
          <Pressable
            accessibilityLabel={control.label}
            accessibilityRole="button"
            key={control.fitMode}
            onPress={() => mapRef.current?.fitTo(control.fitMode)}
            style={styles.mapControlButton}
          >
            <Ionicons color={colors.basalt} name={control.iconName} size={18} />
          </Pressable>
        ))}
      </Animated.View>

      <Animated.View style={[styles.listSheet, sheetStyle]}>
        <GestureDetector gesture={gesture}>
          <View style={styles.handleArea}>
            <View style={styles.grip} />
          </View>
        </GestureDetector>

        {isSearching ? (
          <View style={styles.searchHeader}>
            <Text style={styles.searchHeaderText}>검색 결과</Text>
            <Pressable accessibilityRole="button" onPress={clearSearch}>
              <Text style={styles.searchHeaderAction}>추천 목록으로</Text>
            </Pressable>
          </View>
        ) : (
          <PlaceSourceTabs
            dayNumber={selectedSchedule?.dayNumber ?? 1}
            onSelect={changeTab}
            value={activeTab}
          />
        )}

        {isLoading ? (
          <View style={styles.listState}>
            <ActivityIndicator color={colors.primary} />
          </View>
        ) : isError ? (
          <View style={styles.listState}>
            <Text style={styles.stateTitle}>장소를 불러오지 못했어요</Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => refetch()}
              style={styles.retryButton}
            >
              <Text style={styles.retryText}>다시 시도</Text>
            </Pressable>
          </View>
        ) : (
          <FlatList
            contentContainerStyle={[styles.listContent, { paddingBottom: insets.bottom }]}
            data={places}
            keyExtractor={(place) => place.id}
            keyboardShouldPersistTaps="handled"
            ListEmptyComponent={
              <View style={styles.listState}>
                <Ionicons color={colors.textTertiary} name="search-outline" size={26} />
                <Text style={styles.stateDescription}>
                  {isSearching
                    ? `'${keywordInput}' 에 해당하는 장소를 찾지 못했어요`
                    : PLACE_SOURCE_EMPTY_MESSAGES[activeTab]}
                </Text>
              </View>
            }
            onScrollToIndexFailed={() => undefined}
            ref={listRef}
            renderItem={({ item }) => (
              <PlaceCandidateCard
                isAdded={addedPlaceIds.includes(item.id)}
                isSelected={item.id === selectedPlaceId}
                onPress={selectPlace}
                onPressSelect={openAddSheet}
                place={item}
              />
            )}
            showsVerticalScrollIndicator={false}
            style={styles.list}
          />
        )}

        {addErrorMessage && (
          <View style={[styles.addErrorBar, { paddingBottom: insets.bottom }]}>
            <Text style={styles.addErrorText}>{addErrorMessage}</Text>
          </View>
        )}

        {addedPlaceIds.length > 0 && (
          <View style={[styles.addedBar, { paddingBottom: spacing.sm + 2 + insets.bottom }]}>
            <Text style={styles.addedBarText}>{addedPlaceIds.length}곳을 담았어요</Text>
            <Pressable accessibilityRole="button" onPress={goToTrip} style={styles.addedBarButton}>
              <Text style={styles.addedBarButtonText}>일정으로 돌아가기</Text>
            </Pressable>
          </View>
        )}
      </Animated.View>

      {pendingPlace && (
        <AddScheduleSheet
          initialScheduleId={selectedScheduleId}
          onClose={closeAddSheet}
          onSubmit={addSchedule}
          place={pendingPlace}
          schedules={trip.schedules}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  addErrorBar: {
    backgroundColor: colors.errorBg,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  addErrorText: {
    color: colors.error,
    fontSize: typography.label.fontSize,
    textAlign: 'center',
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  topOverlay: {
    gap: spacing.sm + 2,
    left: 0,
    paddingHorizontal: spacing.md,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  mapControls: {
    gap: spacing.sm,
    position: 'absolute',
    right: spacing.md,
  },
  mapControlButton: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radius.full,
    elevation: 3,
    height: 40,
    justifyContent: 'center',
    shadowColor: colors.basalt,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.16,
    shadowRadius: 6,
    width: 40,
  },
  listSheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl + 4,
    borderTopRightRadius: radius.xl + 4,
    bottom: 0,
    elevation: 8,
    left: 0,
    position: 'absolute',
    right: 0,
    shadowColor: colors.basalt,
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.12,
    shadowRadius: 12,
  },
  handleArea: {
    alignItems: 'center',
    justifyContent: 'center',
    // 손가락으로 잡기 편하도록 눈에 보이는 막대보다 넉넉하게 둔다
    paddingVertical: spacing.sm + 2,
  },
  grip: {
    backgroundColor: colors.border,
    borderRadius: radius.sm,
    height: 5,
    width: 44,
  },
  searchHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  searchHeaderText: {
    color: colors.basalt,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  searchHeaderAction: {
    color: colors.primary,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
  list: {
    flex: 1,
  },
  listContent: {
    flexGrow: 1,
    paddingTop: spacing.sm,
  },
  listState: {
    alignItems: 'center',
    flexGrow: 1,
    gap: spacing.sm,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xl,
  },
  addedBar: {
    alignItems: 'center',
    backgroundColor: colors.leafSoft,
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm + 2,
  },
  addedBarText: {
    color: colors.leaf,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  addedBarButton: {
    backgroundColor: colors.leaf,
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  addedBarButtonText: {
    color: colors.surface,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  centered: {
    alignItems: 'center',
    flex: 1,
    gap: spacing.sm,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  stateTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  stateDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    textAlign: 'center',
  },
  retryButton: {
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  retryText: {
    color: colors.primary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
});
