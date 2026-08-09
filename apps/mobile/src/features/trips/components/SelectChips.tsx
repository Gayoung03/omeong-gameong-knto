import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

export type SelectChipOption<Value extends string> = {
  value: Value;
  label: string;
};

type SelectChipsProps<Value extends string> = {
  options: SelectChipOption<Value>[];
  selectedValue: Value;
  onSelect: (value: Value) => void;
};

export function SelectChips<Value extends string>({
  options,
  selectedValue,
  onSelect,
}: SelectChipsProps<Value>) {
  return (
    <View style={styles.row}>
      {options.map((option) => {
        const isSelected = option.value === selectedValue;

        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: isSelected }}
            key={option.value}
            onPress={() => onSelect(option.value)}
            style={[styles.chip, isSelected && styles.selectedChip]}
          >
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
    flexWrap: 'wrap',
    gap: spacing.xs + 2,
  },
  chip: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.full,
    borderWidth: 1,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 5,
  },
  selectedChip: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  label: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize + 1,
    fontWeight: '600',
  },
  selectedLabel: {
    color: colors.surface,
    fontWeight: '700',
  },
});
