import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, shadow, spacing, typography } from '@/src/theme';
import { INQUIRY_STATUS_LABEL, type InquiryStatus } from '@/src/types/inquiry';

export type InquiryFilter = InquiryStatus | 'all';

const filterOptions: { value: InquiryFilter; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: 'pending', label: INQUIRY_STATUS_LABEL.pending },
  { value: 'completed', label: INQUIRY_STATUS_LABEL.completed },
];

type Props = {
  value: InquiryFilter;
  onChange: (next: InquiryFilter) => void;
};

export function InquiryFilterTabs({ value, onChange }: Props) {
  return (
    <View style={styles.tabs}>
      {filterOptions.map((option) => {
        const isSelected = option.value === value;

        return (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected: isSelected }}
            key={option.value}
            onPress={() => onChange(option.value)}
            style={styles.tab}
          >
            <Text style={[styles.label, isSelected && styles.labelSelected]}>{option.label}</Text>
            {/* 선택되지 않은 탭도 같은 높이를 차지해 라벨이 흔들리지 않는다. */}
            <View style={[styles.indicator, isSelected && styles.indicatorSelected]} />
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  indicator: {
    backgroundColor: 'transparent',
    borderRadius: 999,
    height: 2,
    marginTop: spacing.sm,
    width: '60%',
  },
  indicatorSelected: {
    backgroundColor: colors.primary,
  },
  label: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    fontWeight: '600',
  },
  labelSelected: {
    color: colors.primary,
    fontWeight: '700',
  },
  tab: {
    alignItems: 'center',
    flex: 1,
    paddingTop: spacing.md,
  },
  tabs: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    flexDirection: 'row',
    overflow: 'hidden',
    ...shadow.sm,
  },
});
