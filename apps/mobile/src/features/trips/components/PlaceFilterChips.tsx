import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import { PLACE_FILTER_OPTIONS } from '../constants/placeSearch';
import type { PlaceFilter } from '../types/trip';

type PlaceFilterChipsProps = {
  /** 선택된 필터. 없으면 전체 */
  value: PlaceFilter | null;
  onSelect: (filter: PlaceFilter) => void;
};

const CHIP_COLORS: Record<PlaceFilter, string> = {
  restaurant: colors.primary,
  attraction: colors.leaf,
  accommodation: colors.sea,
};

/** 지도 위 카테고리 필터. 같은 칩을 다시 누르면 해제된다 */
export function PlaceFilterChips({ value, onSelect }: PlaceFilterChipsProps) {
  return (
    <View style={styles.row}>
      {PLACE_FILTER_OPTIONS.map((option) => {
        const isSelected = option.value === value;
        const accent = CHIP_COLORS[option.value];

        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: isSelected }}
            key={option.value}
            onPress={() => onSelect(option.value)}
            style={[styles.chip, isSelected && { backgroundColor: accent, borderColor: accent }]}
          >
            <Ionicons
              color={isSelected ? colors.surface : accent}
              name={option.iconName}
              size={14}
            />
            <Text style={[styles.label, isSelected && styles.selectedLabel]}>{option.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  chip: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.full,
    borderWidth: 1,
    elevation: 2,
    flexDirection: 'row',
    gap: spacing.xs + 1,
    paddingHorizontal: spacing.md - 2,
    paddingVertical: spacing.sm,
    shadowColor: colors.basalt,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.12,
    shadowRadius: 5,
  },
  label: {
    color: colors.basalt,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  selectedLabel: {
    color: colors.surface,
  },
});
