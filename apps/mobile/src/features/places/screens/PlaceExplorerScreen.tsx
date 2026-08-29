import Ionicons from '@expo/vector-icons/Ionicons';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { PetPolicyBadge } from '@/src/components/domain/PetPolicyBadge';
import { ErrorState } from '@/src/components/feedback/ErrorState';
import { RemoteImage } from '@/src/components/ui/RemoteImage';
import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import {
  useSavedPlaceIds,
  useToggleSavedPlace,
} from '@/src/features/saved/hooks/useSavedPlaces';
import { useDebounce } from '@/src/hooks/useDebounce';
import { colors, spacing } from '@/src/theme';

import { InteractivePlaceMap } from '../components/InteractivePlaceMap';
import { placeCategories } from '../constants/placeCategories';
import { usePlaces } from '../hooks/usePlaces';
import { isPlaceRegion, placeRegions, type PlaceRegionFilter } from '../constants/placeRegions';
import type { Place } from '../types/place';

type ViewMode = 'list' | 'map';

export function PlaceExplorerScreen() {
  const { region, view } = useLocalSearchParams<{ region?: string; view?: string }>();
  const regionScrollRef = useRef<ScrollView>(null);
  const [query, setQuery] = useState('');
  const [selectedRegion, setSelectedRegion] = useState<PlaceRegionFilter>(() =>
    region && isPlaceRegion(region) ? region : '전체',
  );
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>(view === 'map' ? 'map' : 'list');
  const debouncedQuery = useDebounce(query.trim());
  const selectedCategoryConfig = placeCategories.find(({ id }) => id === selectedCategory);
  const environment =
    selectedCategory === 'indoor'
      ? ('indoor' as const)
      : selectedCategory === 'outdoor'
        ? ('outdoor' as const)
        : undefined;
  const filters = useMemo(
    () => ({
      categories: selectedCategoryConfig?.serverCategories,
      environment,
      q: debouncedQuery || undefined,
      region: selectedRegion === '전체' ? undefined : selectedRegion,
    }),
    [debouncedQuery, environment, selectedCategoryConfig, selectedRegion],
  );
  const {
    data,
    error,
    fetchNextPage,
    hasNextPage,
    isError,
    isFetchNextPageError,
    isFetchingNextPage,
    isPending,
    refetch,
  } = usePlaces(filters);
  const savedPlaceIds = useSavedPlaceIds();
  const toggleSavedPlace = useToggleSavedPlace();

  const places = useMemo(() => {
    const unique = new Map<string, Place>();
    data?.pages.forEach((page) => page.items.forEach((place) => unique.set(place.id, place)));
    return [...unique.values()];
  }, [data]);

  useEffect(() => {
    const selectedIndex = placeRegions.indexOf(selectedRegion);
    regionScrollRef.current?.scrollTo({
      animated: false,
      x: Math.max(0, selectedIndex * 116 - 28),
    });
  }, [selectedRegion]);

  const toggleFavorite = (place: Place) => {
    toggleSavedPlace.mutate({ isSaved: savedPlaceIds.has(place.id), placeId: place.id });
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScreenHeader title="장소 탐색" />

      <View style={styles.searchBar}>
        <Ionicons color={colors.iconGray} name="search-outline" size={20} />
        <TextInput
          onChangeText={setQuery}
          placeholder="제주에서 갈 장소를 검색해보세요"
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

      <ScrollView
        contentContainerStyle={styles.regionContent}
        horizontal
        ref={regionScrollRef}
        showsHorizontalScrollIndicator={false}
        style={styles.regionScroll}
      >
        {placeRegions.map((region) => {
          const isSelected = region === selectedRegion;
          return (
            <Pressable
              accessibilityRole="button"
              key={region}
              onPress={() => setSelectedRegion(region)}
              style={({ pressed }) => [
                styles.regionChip,
                isSelected && styles.regionChipSelected,
                pressed && styles.pressed,
              ]}
            >
              <Text style={[styles.regionText, isSelected && styles.regionTextSelected]}>
                {region}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      <ScrollView
        contentContainerStyle={styles.categoryContent}
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.categoryScroll}
      >
        {placeCategories.map((category) => {
          const isSelected = category.id === selectedCategory;
          return (
            <Pressable
              accessibilityRole="button"
              key={category.id}
              onPress={() =>
                setSelectedCategory((currentCategory) =>
                    currentCategory === category.id ? null : category.id,
                )
              }
              style={({ pressed }) => [
                styles.categoryItem,
                isSelected && styles.categoryItemSelected,
                pressed && styles.pressed,
              ]}
            >
              <Ionicons
                color={isSelected ? colors.primary : colors.textStrong}
                name={category.icon}
                size={23}
              />
              <Text style={[styles.categoryText, isSelected && styles.categoryTextSelected]}>
                {category.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      <View style={styles.segmentedControl}>
        <ModeButton
          icon="list"
          isSelected={viewMode === 'list'}
          label="리스트"
          onPress={() => setViewMode('list')}
        />
        <ModeButton
          icon="location-outline"
          isSelected={viewMode === 'map'}
          label="지도"
          onPress={() => setViewMode('map')}
        />
      </View>

      {viewMode === 'list' ? (
        <FlatList
          contentContainerStyle={styles.listContent}
          data={places}
          keyExtractor={(place) => place.id}
          ListEmptyComponent={
            isPending ? (
              <View style={styles.loading}>
                <ActivityIndicator color={colors.primary} />
              </View>
            ) : isError ? (
              <View style={styles.errorContainer}>
                <ErrorState error={error} onRetry={() => void refetch()} />
              </View>
            ) : (
              <EmptyResult />
            )
          }
          ListFooterComponent={
            isFetchingNextPage ? (
              <ActivityIndicator color={colors.primary} style={styles.pageLoading} />
            ) : isFetchNextPageError ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => void fetchNextPage()}
                style={({ pressed }) => [styles.pageRetry, pressed && styles.pressed]}
              >
                <Text style={styles.pageRetryText}>추가 장소를 불러오지 못했어요 · 다시 시도</Text>
              </Pressable>
            ) : null
          }
          onEndReached={() => {
            if (hasNextPage && !isFetchingNextPage) void fetchNextPage();
          }}
          onEndReachedThreshold={0.4}
          renderItem={({ item }) => (
            <PlaceRow
              isFavorite={savedPlaceIds.has(item.id)}
              onPressFavorite={() => toggleFavorite(item)}
              place={item}
            />
          )}
          showsVerticalScrollIndicator={false}
          style={styles.resultsList}
        />
      ) : (
        isError ? (
          <ErrorState error={error} onRetry={() => void refetch()} />
        ) : isPending ? (
          <View style={styles.loading}>
            <ActivityIndicator color={colors.primary} />
          </View>
        ) : (
          <InteractivePlaceMap places={places} />
        )
      )}
    </SafeAreaView>
  );
}

type ModeButtonProps = {
  icon: 'list' | 'location-outline';
  label: string;
  isSelected: boolean;
  onPress: () => void;
};

function ModeButton({ icon, isSelected, label, onPress }: ModeButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.modeButton,
        isSelected && styles.modeButtonSelected,
        pressed && styles.pressed,
      ]}
    >
      <Ionicons color={isSelected ? colors.surface : colors.textStrong} name={icon} size={18} />
      <Text style={[styles.modeText, isSelected && styles.modeTextSelected]}>{label}</Text>
    </Pressable>
  );
}

type PlaceRowProps = {
  place: Place;
  isFavorite: boolean;
  onPressFavorite: () => void;
};

function PlaceRow({ isFavorite, onPressFavorite, place }: PlaceRowProps) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push(`/places/${place.id}`)}
      style={({ pressed }) => [styles.placeRow, pressed && styles.rowPressed]}
    >
      <RemoteImage style={styles.placeImage} uri={place.imageUrl ?? undefined} />
      <View style={styles.placeCopy}>
        <Text numberOfLines={1} style={styles.placeName}>
          {place.name}
        </Text>
        <Text numberOfLines={1} style={styles.address}>
          {place.address}
        </Text>
        <View style={styles.tagRow}>
          {/* 동반 정책은 5종 배지로 그린다. 정보가 없는 장소도 회색 배지가 자리를 지켜
              카드 높이가 들쭉날쭉해지지 않는다. */}
          {place.petPolicy ? <PetPolicyBadge petPolicy={place.petPolicy} /> : null}
          <View style={styles.categoryTag}>
            <Text style={styles.categoryTagText}>{place.category}</Text>
          </View>
        </View>
      </View>
      <View style={styles.placeMeta}>
        <Pressable
          accessibilityLabel={isFavorite ? '즐겨찾기 해제' : '즐겨찾기 추가'}
          hitSlop={10}
          onPress={(event) => {
            event.stopPropagation();
            onPressFavorite();
          }}
        >
          <Ionicons
            color={isFavorite ? colors.primary : colors.textSecondary}
            name={isFavorite ? 'heart' : 'heart-outline'}
            size={22}
          />
        </Pressable>
        {place.distanceKm === null ? null : (
          <Text style={styles.distance}>{place.distanceKm.toFixed(1)}km</Text>
        )}
      </View>
    </Pressable>
  );
}

function EmptyResult() {
  return (
    <View style={styles.emptyContainer}>
      <Ionicons color={colors.textTertiary} name="search-outline" size={34} />
      <Text style={styles.emptyTitle}>조건에 맞는 장소가 없어요</Text>
      <Text style={styles.emptyDescription}>다른 지역이나 카테고리를 선택해보세요.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  pressed: {
    opacity: 0.58,
  },
  searchBar: {
    height: 40,
    flexShrink: 0,
    marginHorizontal: spacing.md,
    marginTop: 8,
    paddingHorizontal: 11,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    borderWidth: 1,
    borderColor: colors.divider,
    borderRadius: 13,
    backgroundColor: colors.surface,
  },
  searchInput: {
    flex: 1,
    paddingVertical: 0,
    color: colors.textPrimary,
    fontSize: 13,
  },
  regionContent: {
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    gap: 7,
  },
  regionScroll: {
    flexGrow: 0,
    flexShrink: 0,
    height: 51,
  },
  regionChip: {
    height: 31,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: colors.divider,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  regionChipSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primary,
  },
  regionText: {
    color: colors.textStrong,
    fontSize: 12,
    fontWeight: '600',
  },
  regionTextSelected: {
    color: colors.surface,
    fontWeight: '800',
  },
  categoryContent: {
    paddingHorizontal: spacing.md,
    paddingBottom: 9,
    gap: 7,
  },
  categoryScroll: {
    flexGrow: 0,
    flexShrink: 0,
    height: 62,
  },
  categoryItem: {
    width: 59,
    height: 53,
    borderWidth: 1,
    borderColor: colors.divider,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
    backgroundColor: colors.surface,
  },
  categoryItemSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primarySoft,
  },
  categoryText: {
    color: colors.textStrong,
    fontSize: 10,
    fontWeight: '600',
  },
  categoryTextSelected: {
    color: colors.primary,
    fontWeight: '800',
  },
  segmentedControl: {
    height: 36,
    flexShrink: 0,
    marginHorizontal: spacing.md,
    marginBottom: 8,
    padding: 2,
    flexDirection: 'row',
    gap: 4,
    borderRadius: 10,
    backgroundColor: colors.neutralGray,
  },
  modeButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 8,
  },
  modeButtonSelected: {
    backgroundColor: colors.primary,
  },
  modeText: {
    color: colors.textStrong,
    fontSize: 13,
    fontWeight: '700',
  },
  modeTextSelected: {
    color: colors.surface,
  },
  loading: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
  },
  errorContainer: {
    minHeight: 280,
  },
  pageLoading: {
    paddingVertical: spacing.md,
  },
  pageRetry: {
    alignItems: 'center',
    paddingVertical: spacing.md,
  },
  pageRetryText: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: '700',
  },
  listContent: {
    paddingHorizontal: spacing.md,
    paddingBottom: 20,
  },
  resultsList: {
    flex: 1,
    minHeight: 0,
  },
  placeRow: {
    minHeight: 101,
    paddingVertical: 9,
    flexDirection: 'row',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.divider,
  },
  rowPressed: {
    opacity: 0.68,
  },
  placeImage: {
    width: 108,
    height: 83,
    borderRadius: 12,
    backgroundColor: colors.border,
  },
  placeCopy: {
    flex: 1,
    paddingHorizontal: 10,
    paddingVertical: 2,
  },
  placeName: {
    color: colors.textPrimary,
    fontSize: 15,
    fontWeight: '800',
  },
  address: {
    marginTop: 4,
    color: colors.textSecondary,
    fontSize: 11,
  },
  tagRow: {
    marginTop: 9,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  categoryTag: {
    height: 20,
    paddingHorizontal: 7,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 6,
    backgroundColor: colors.seaSoft,
  },
  categoryTagText: {
    color: colors.seaDeep,
    fontSize: 9,
    fontWeight: '700',
  },
  placeMeta: {
    width: 43,
    paddingVertical: 3,
    alignItems: 'flex-end',
    justifyContent: 'space-between',
  },
  distance: {
    color: colors.textSecondary,
    fontSize: 10,
  },
  emptyContainer: {
    paddingTop: 80,
    alignItems: 'center',
  },
  emptyTitle: {
    marginTop: 13,
    color: colors.textPrimary,
    fontSize: 15,
    fontWeight: '700',
  },
  emptyDescription: {
    marginTop: 5,
    color: colors.textSecondary,
    fontSize: 12,
  },
});
