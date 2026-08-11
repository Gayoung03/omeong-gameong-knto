import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import { PLACE_SOURCE_TAB_OPTIONS } from '../constants/placeSearch';
import type { PlaceSourceTab } from '../types/trip';

type PlaceSourceTabsProps = {
  value: PlaceSourceTab;
  onSelect: (tab: PlaceSourceTab) => void;
  /** 추천 탭에 붙일 날짜 번호 (예: Day 1 추천) */
  dayNumber: number;
};

export function PlaceSourceTabs({ value, onSelect, dayNumber }: PlaceSourceTabsProps) {
  return (
    <ScrollView
      contentContainerStyle={styles.content}
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.container}
    >
      {PLACE_SOURCE_TAB_OPTIONS.map((option) => {
        const isSelected = option.value === value;
        const label =
          option.value === 'dayRecommend' ? `Day ${dayNumber} ${option.label}` : option.label;

        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: isSelected }}
            key={option.value}
            onPress={() => onSelect(option.value)}
            style={[styles.tab, isSelected && styles.selectedTab]}
          >
            <Text style={[styles.label, isSelected && styles.selectedLabel]}>{label}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    // 가로 ScrollView 는 높이가 정해지지 않으면 부모 높이에 눌려 잘린다
    flexGrow: 0,
    flexShrink: 0,
  },
  content: {
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  tab: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.full,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  selectedTab: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primary,
  },
  label: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  selectedLabel: {
    color: colors.primary,
  },
});
