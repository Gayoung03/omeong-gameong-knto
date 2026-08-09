import Ionicons from '@expo/vector-icons/Ionicons';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  FlatList,
  Image,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { colors, spacing } from '@/src/theme';

import { InteractivePlaceMap } from '../components/InteractivePlaceMap';
import { mockPlaces, placeCategories } from '../data/placeMockData';
import { isPlaceRegion, placeRegions, type PlaceRegionFilter } from '../data/placeRegions';
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
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(
    () => new Set(mockPlaces.filter((place) => place.initiallyFavorite).map((place) => place.id)),
  );

  useEffect(() => {
    const selectedIndex = placeRegions.indexOf(selectedRegion);
    regionScrollRef.current?.scrollTo({
      animated: false,
      x: Math.max(0, selectedIndex * 116 - 28),
    });
  }, [selectedRegion]);

  const filteredPlaces = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('ko-KR');

    return mockPlaces.filter((place) => {
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
  }, [query, selectedCategory, selectedRegion]);

  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
      return;
    }

    router.replace('/');
  };

  const toggleFavorite = (placeId: string) => {
    setFavoriteIds((currentIds) => {
      const nextIds = new Set(currentIds);
      if (nextIds.has(placeId)) {
        nextIds.delete(placeId);
      } else {
        nextIds.add(placeId);
      }
      return nextIds;
    });
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Pressable
          accessibilityLabel="홈으로 돌아가기"
          hitSlop={12}
          onPress={handleBack}
          style={({ pressed }) => [styles.backButton, pressed && styles.pressed]}
        >
          <Ionicons color={colors.textPrimary} name="chevron-back" size={26} />
        </Pressable>
        <Text style={styles.headerTitle}>장소 탐색</Text>
        <View style={styles.headerSpacer} />
      </View>

      <View style={styles.searchBar}>
        <Ionicons color="#8A8A8A" name="search-outline" size={20} />
        <TextInput
          onChangeText={setQuery}
          placeholder="제주에서 갈 장소를 검색해보세요"
          placeholderTextColor="#9A9A9A"
          returnKeyType="search"
          style={styles.searchInput}
          value={query}
        />
        {query ? (
          <Pressable accessibilityLabel="검색어 지우기" hitSlop={8} onPress={() => setQuery('')}>
            <Ionicons color="#929292" name="close-circle" size={19} />
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
          const isSelected = category.label === selectedCategory;
          return (
            <Pressable
              accessibilityRole="button"
              key={category.id}
              onPress={() =>
                setSelectedCategory((currentCategory) =>
                  currentCategory === category.label ? null : category.label,
                )
              }
              style={({ pressed }) => [
                styles.categoryItem,
                isSelected && styles.categoryItemSelected,
                pressed && styles.pressed,
              ]}
            >
              <Ionicons
                color={isSelected ? colors.primary : '#3D4A48'}
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
          data={filteredPlaces}
          keyExtractor={(place) => place.id}
          ListEmptyComponent={<EmptyResult />}
          renderItem={({ item }) => (
            <PlaceRow
              isFavorite={favoriteIds.has(item.id)}
              onPressFavorite={() => toggleFavorite(item.id)}
              place={item}
            />
          )}
          showsVerticalScrollIndicator={false}
          style={styles.resultsList}
        />
      ) : (
        <InteractivePlaceMap places={filteredPlaces} />
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
      <Ionicons color={isSelected ? colors.surface : '#535353'} name={icon} size={18} />
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
      <Image
        accessibilityLabel={`${place.name} 사진`}
        source={{ uri: place.imageUrl }}
        style={styles.placeImage}
      />
      <View style={styles.placeCopy}>
        <Text numberOfLines={1} style={styles.placeName}>
          {place.name}
        </Text>
        <Text numberOfLines={1} style={styles.address}>
          {place.address}
        </Text>
        <View style={styles.tagRow}>
          {place.petFriendly ? (
            <View style={styles.petTag}>
              <Ionicons color="#D7673D" name="paw" size={10} />
              <Text style={styles.petTagText}>반려동물 동반 가능</Text>
            </View>
          ) : null}
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
            color={isFavorite ? '#FF5A43' : '#777777'}
            name={isFavorite ? 'heart' : 'heart-outline'}
            size={22}
          />
        </Pressable>
        <Text style={styles.distance}>{place.distanceKm.toFixed(1)}km</Text>
      </View>
    </Pressable>
  );
}

function EmptyResult() {
  return (
    <View style={styles.emptyContainer}>
      <Ionicons color="#B8B8B8" name="search-outline" size={34} />
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
  header: {
    height: 52,
    flexShrink: 0,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#ECECEC',
  },
  backButton: {
    width: 42,
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.58,
  },
  headerTitle: {
    flex: 1,
    color: colors.textPrimary,
    fontSize: 17,
    fontWeight: '800',
    textAlign: 'center',
  },
  headerSpacer: {
    width: 42,
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
    borderColor: '#DEDEDE',
    borderRadius: 13,
    backgroundColor: '#FFFFFF',
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
    borderColor: '#E5E5E5',
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
  },
  regionChipSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primary,
  },
  regionText: {
    color: '#555555',
    fontSize: 12,
    fontWeight: '600',
  },
  regionTextSelected: {
    color: '#FFFFFF',
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
    borderColor: '#E9E9E9',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
    backgroundColor: '#FFFFFF',
  },
  categoryItemSelected: {
    borderColor: colors.primary,
    backgroundColor: '#FFF3EA',
  },
  categoryText: {
    color: '#565656',
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
    backgroundColor: '#F3F3F3',
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
    color: '#4F4F4F',
    fontSize: 13,
    fontWeight: '700',
  },
  modeTextSelected: {
    color: '#FFFFFF',
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
    borderBottomColor: '#E5E5E5',
  },
  rowPressed: {
    opacity: 0.68,
  },
  placeImage: {
    width: 108,
    height: 83,
    borderRadius: 12,
    backgroundColor: '#ECECEC',
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
  petTag: {
    height: 20,
    paddingHorizontal: 6,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    borderRadius: 6,
    backgroundColor: '#FFF1E9',
  },
  petTagText: {
    color: '#B85635',
    fontSize: 9,
    fontWeight: '700',
  },
  categoryTag: {
    height: 20,
    paddingHorizontal: 7,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 6,
    backgroundColor: '#E8F8F3',
  },
  categoryTagText: {
    color: '#238871',
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
    color: '#666666',
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
