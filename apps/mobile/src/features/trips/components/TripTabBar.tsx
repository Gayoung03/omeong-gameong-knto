import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/src/theme';

import type { TripDetailTab } from '../types/trip';

type TripTabBarProps = {
  activeTab: TripDetailTab;
  onChangeTab: (tab: TripDetailTab) => void;
};

const TAB_ITEMS: { value: TripDetailTab; label: string }[] = [
  { value: 'schedule', label: '일정' },
  { value: 'map', label: '지도' },
  { value: 'checklist', label: '체크리스트' },
  { value: 'memo', label: '메모' },
];

export function TripTabBar({ activeTab, onChangeTab }: TripTabBarProps) {
  return (
    <View style={styles.container}>
      {TAB_ITEMS.map((item) => {
        const isActive = item.value === activeTab;

        return (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected: isActive }}
            key={item.value}
            onPress={() => onChangeTab(item.value)}
            style={styles.tab}
          >
            <Text style={[styles.label, isActive && styles.activeLabel]}>{item.label}</Text>
            <View style={[styles.indicator, isActive && styles.activeIndicator]} />
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    marginHorizontal: spacing.md,
    marginTop: spacing.sm + 4,
  },
  tab: {
    alignItems: 'center',
    flex: 1,
    paddingTop: spacing.sm + 1,
  },
  label: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize + 1,
    fontWeight: typography.label.fontWeight,
  },
  activeLabel: {
    color: colors.primary,
    fontWeight: '700',
  },
  indicator: {
    backgroundColor: 'transparent',
    borderRadius: 3,
    height: 3,
    marginTop: spacing.sm + 2,
    width: '60%',
  },
  activeIndicator: {
    backgroundColor: colors.primary,
  },
});
