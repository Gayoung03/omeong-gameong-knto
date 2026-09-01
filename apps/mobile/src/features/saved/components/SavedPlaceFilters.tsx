import Ionicons from '@expo/vector-icons/Ionicons';
import { useMemo } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { placeCategories } from '@/src/features/places/constants/placeCategories';
import { placeRegions, type PlaceRegionFilter } from '@/src/features/places/constants/placeRegions';
import { colors, spacing } from '@/src/theme';

import type { SavedPlace } from '../types/saved';

/**
 * 저장한 장소를 지역·분류로 좁히는 칩 두 줄.
 *
 * **저장 목록에 실제로 있는 값만 그린다.** 장소 탐색은 1268곳을 다루므로 지역 6종과
 * 분류 7종을 고정으로 깔지만, 저장 목록은 스무 건 남짓이라 그렇게 하면 절반이 눌러도
 * 0건인 칩이 된다. 고를 것이 하나뿐인 줄은 아예 그리지 않는다 — 누를 이유가 없다.
 *
 * 칩 생김새와 토글 방식(지역은 '전체' 칩, 분류는 다시 눌러 해제)은 장소 탐색을 그대로
 * 따랐다. 두 화면을 오갈 때 같은 칩이 같은 자리에 있어야 한다.
 * 치수는 `places/screens/PlaceExplorerScreen.tsx` 의 `regionChip` · `categoryItem` 에서 옮겼다.
 */

/**
 * 분류 줄에서 빼는 칩.
 *
 * 탐색 화면의 `placeCategories` 에는 '실내' · '야외' 가 섞여 있는데 그 둘은 분류가 아니라
 * `environment` 를 거른다. `SavedPlace` 에는 그 값이 없으므로 여기서는 다루지 않는다.
 */
const ENVIRONMENT_CATEGORY_IDS = new Set(['indoor', 'outdoor']);

type SavedPlaceFiltersProps = {
  places: SavedPlace[];
  selectedRegion: PlaceRegionFilter;
  selectedCategory: string | null;
  onSelectRegion: (region: PlaceRegionFilter) => void;
  onSelectCategory: (category: string | null) => void;
};

export function SavedPlaceFilters({
  places,
  selectedRegion,
  selectedCategory,
  onSelectRegion,
  onSelectCategory,
}: SavedPlaceFiltersProps) {
  const regions = useMemo(() => {
    const saved = new Set(places.map((place) => place.region));
    // 칩 순서는 탐색 화면과 같아야 하므로 상수 순서를 유지한 채 걸러 낸다.
    return placeRegions.filter((region) => region === '전체' || saved.has(region));
  }, [places]);

  const categories = useMemo(() => {
    const saved = new Set(places.map((place) => place.category));
    // 어댑터가 라벨로 못 옮긴 서버 코드(`etc` 등)는 칩을 만들지 않는다. 영문 코드가
    // 칩에 그대로 뜨는 것보다 '전체' 에서만 보이는 편이 낫다 — 탐색 화면과 같은 규칙.
    return placeCategories.filter(
      (category) => !ENVIRONMENT_CATEGORY_IDS.has(category.id) && saved.has(category.label),
    );
  }, [places]);

  // '전체' 말고 고를 지역이 없거나, 분류가 한 종류뿐이면 그 줄은 필터 구실을 못 한다.
  const showRegions = regions.length > 2;
  const showCategories = categories.length > 1;

  if (!showRegions && !showCategories) return null;

  return (
    <View>
      {showRegions ? (
        <ScrollView
          contentContainerStyle={styles.regionContent}
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.regionScroll}
        >
          {regions.map((region) => {
            const isSelected = region === selectedRegion;
            return (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                key={region}
                onPress={() => onSelectRegion(region)}
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
      ) : null}

      {showCategories ? (
        <ScrollView
          contentContainerStyle={styles.categoryContent}
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.categoryScroll}
        >
          {categories.map((category) => {
            const isSelected = category.label === selectedCategory;
            return (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                key={category.id}
                // 선택된 칩을 다시 누르면 해제다. 그래서 '전체' 칩이 따로 없다.
                onPress={() => onSelectCategory(isSelected ? null : category.label)}
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
                <Text
                  numberOfLines={1}
                  style={[styles.categoryText, isSelected && styles.categoryTextSelected]}
                >
                  {/* 필터 값인 `label` 대신 표시용 글자를 그린다. 라벨이 길면 칩에서 잘린다. */}
                  {category.chipLabel ?? category.label}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  categoryContent: {
    gap: 7,
    paddingBottom: 9,
    paddingHorizontal: spacing.md,
  },
  categoryItem: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.divider,
    borderRadius: 12,
    borderWidth: 1,
    gap: 3,
    height: 53,
    justifyContent: 'center',
    width: 59,
  },
  categoryItemSelected: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primary,
  },
  categoryScroll: {
    flexGrow: 0,
    flexShrink: 0,
    height: 62,
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
  pressed: {
    opacity: 0.58,
  },
  regionChip: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.divider,
    borderRadius: 16,
    borderWidth: 1,
    height: 31,
    justifyContent: 'center',
    paddingHorizontal: 16,
  },
  regionChipSelected: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  regionContent: {
    gap: 7,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  regionScroll: {
    flexGrow: 0,
    flexShrink: 0,
    height: 51,
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
});
