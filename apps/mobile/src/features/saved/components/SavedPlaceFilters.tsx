import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { placeCategories } from '@/src/features/places/constants/placeCategories';
import { placeRegions, type PlaceRegionFilter } from '@/src/features/places/constants/placeRegions';
import { colors, spacing } from '@/src/theme';

/**
 * 저장한 장소를 지역·분류로 좁히는 칩 두 줄.
 *
 * 지역·카테고리 종류와 토글 방식은 장소 탐색을 그대로 따른다. 두 화면을 오갈 때
 * 같은 칩이 같은 위치에 있어야 필터 방식을 다시 익힐 필요가 없다.
 * 치수는 `places/screens/PlaceExplorerScreen.tsx` 의 `regionChip` · `categoryItem` 에서 옮겼다.
 */

type SavedPlaceFiltersProps = {
  selectedRegion: PlaceRegionFilter;
  selectedCategory: string | null;
  onSelectRegion: (region: PlaceRegionFilter) => void;
  onSelectCategory: (category: string | null) => void;
};

export function SavedPlaceFilters({
  selectedRegion,
  selectedCategory,
  onSelectRegion,
  onSelectCategory,
}: SavedPlaceFiltersProps) {
  return (
    <View>
      <ScrollView
        contentContainerStyle={styles.regionContent}
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.regionScroll}
      >
        {placeRegions.map((region) => {
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
