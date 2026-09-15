import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { EmptyState } from '@/src/components/feedback/EmptyState';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import type { PlaceRegionFilter } from '@/src/features/places/constants/placeRegions';
import { colors, spacing } from '@/src/theme';

import { SavedPlaceCard } from '../components/SavedPlaceCard';
import { SavedPlaceFilters } from '../components/SavedPlaceFilters';
import { useRemoveSavedPlace, useSavedPlaces } from '../hooks/useSavedPlaces';
import type { SavedPlace } from '../types/saved';

type SortBy = 'recent' | 'name';

const SORT_OPTIONS: { label: string; value: SortBy }[] = [
  { label: '최근 저장순', value: 'recent' },
  { label: '이름순', value: 'name' },
];

function sortPlaces(places: SavedPlace[], sortBy: SortBy): SavedPlace[] {
  if (sortBy === 'name') {
    return [...places].sort((a, b) => a.name.localeCompare(b.name, 'ko-KR'));
  }

  // 서버가 이미 저장 시각 내림차순으로 준다. 그래도 명시적으로 정렬해야
  // 이름순으로 갔다가 돌아왔을 때 원래 순서가 그대로 복구된다.
  return [...places].sort((a, b) => b.savedAt.localeCompare(a.savedAt));
}

export function SavedPlacesScreen() {
  const { data: places = [], isPending } = useSavedPlaces();
  const removePlace = useRemoveSavedPlace();
  const [selectedRegion, setSelectedRegion] = useState<PlaceRegionFilter>('전체');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortBy>('recent');
  const [query, setQuery] = useState('');

  const visiblePlaces = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('ko-KR');
    const filtered = places.filter((place) => {
      const matchesQuery =
        !normalizedQuery ||
        place.name.toLocaleLowerCase('ko-KR').includes(normalizedQuery) ||
        place.address.toLocaleLowerCase('ko-KR').includes(normalizedQuery);
      const matchesRegion = selectedRegion === '전체' || place.region === selectedRegion;
      const matchesCategory = !selectedCategory
        ? true
        : selectedCategory === '실내' || selectedCategory === '야외'
          ? place.environment === selectedCategory
          : place.category === selectedCategory;

      return matchesQuery && matchesRegion && matchesCategory;
    });

    return sortPlaces(filtered, sortBy);
  }, [places, query, selectedCategory, selectedRegion, sortBy]);

  const resetFilters = () => {
    setQuery('');
    setSelectedRegion('전체');
    setSelectedCategory(null);
  };

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="저장한 장소" />

      {isPending ? (
        <View style={styles.loading}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : places.length === 0 ? (
        <EmptyState
          actionLabel="장소 탐색으로 가기"
          description="장소 탐색에서 하트를 누르면 여기에 모입니다."
          icon="bookmark-outline"
          onPressAction={() => router.push('/place-explorer')}
          title="아직 저장한 장소가 없어요"
        />
      ) : (
        <>
          <View style={styles.searchBar}>
            <Ionicons color={colors.iconGray} name="search-outline" size={20} />
            <TextInput
              accessibilityLabel="저장한 장소 검색"
              onChangeText={setQuery}
              placeholder="저장한 장소를 검색해보세요"
              placeholderTextColor={colors.textTertiary}
              returnKeyType="search"
              style={styles.searchInput}
              value={query}
            />
            {query ? (
              <Pressable accessibilityLabel="검색어 지우기" hitSlop={8} onPress={() => setQuery('')}>
                <Ionicons color={colors.iconGray} name="close-circle" size={19} />
              </Pressable>
            ) : null}
          </View>

          {/* 칩과 건수는 고정이다. 목록만 스크롤해야 얼마나 좁혀졌는지가 계속 보인다. */}
          <SavedPlaceFilters
            onSelectCategory={setSelectedCategory}
            onSelectRegion={setSelectedRegion}
            selectedCategory={selectedCategory}
            selectedRegion={selectedRegion}
          />

          {/* 0건일 때는 아래 안내가 이미 말해 주므로 띄우지 않는다. 정렬할 것도 없다. */}
          {visiblePlaces.length === 0 ? null : (
            <View style={styles.summary}>
              <Text style={styles.resultCount}>총 {visiblePlaces.length}곳</Text>

              <View style={styles.sortGroup}>
                {SORT_OPTIONS.map((option) => {
                  const isSelected = option.value === sortBy;
                  return (
                    <Pressable
                      accessibilityRole="button"
                      accessibilityState={{ selected: isSelected }}
                      hitSlop={8}
                      key={option.value}
                      onPress={() => setSortBy(option.value)}
                      style={({ pressed }) => [styles.sortButton, pressed && styles.pressed]}
                    >
                      <Text style={[styles.sortLabel, isSelected && styles.sortLabelSelected]}>
                        {option.label}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>
            </View>
          )}

          {visiblePlaces.length === 0 ? (
            // 저장해 둔 장소는 있는데 칩이 다 걸러 낸 경우다. 여기서 '장소 탐색으로
            // 가기' 를 띄우면 저장한 것이 하나도 없는 것처럼 읽힌다.
            <EmptyState
              actionLabel="검색·필터 초기화"
              description="검색어나 지역, 카테고리를 바꿔 보세요."
              icon="funnel-outline"
              onPressAction={resetFilters}
              title="조건에 맞는 장소가 없어요"
            />
          ) : (
            <ScrollView contentContainerStyle={styles.content}>
              <View style={styles.list}>
                {visiblePlaces.map((place) => (
                  <SavedPlaceCard
                    key={place.id}
                    onPress={() =>
                      router.push({ pathname: '/places/[placeId]', params: { placeId: place.id } })
                    }
                    onPressRemove={() => removePlace.mutate(place.id)}
                    place={place}
                  />
                ))}
              </View>
            </ScrollView>
          )}
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
  },
  list: {
    gap: spacing.sm,
  },
  loading: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
  },
  resultCount: {
    color: colors.textSecondary,
    fontSize: 11,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  searchBar: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.divider,
    borderRadius: 13,
    borderWidth: 1,
    flexDirection: 'row',
    flexShrink: 0,
    gap: 7,
    height: 40,
    marginHorizontal: spacing.md,
    marginTop: 8,
    paddingHorizontal: 11,
  },
  searchInput: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: 13,
    paddingVertical: 0,
  },
  sortButton: {
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 32,
    paddingHorizontal: spacing.xs,
  },
  sortGroup: {
    flexDirection: 'row',
    gap: spacing.xs,
    marginRight: -spacing.xs,
  },
  sortLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: '600',
  },
  sortLabelSelected: {
    color: colors.primary,
    fontWeight: '800',
  },
  pressed: {
    opacity: 0.58,
  },
  summary: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
    marginHorizontal: spacing.md,
    // 카테고리 칩과 정렬 라벨이 붙어 보이지 않게 간격을 둔다.
    marginTop: spacing.xs,
  },
});
