import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { ChecklistItem } from '../types/trip';

type ChecklistRowProps = {
  item: ChecklistItem;
  isEditing: boolean;
  onToggle: (itemId: string) => void;
  onRemove: (itemId: string) => void;
};

export function ChecklistRow({ item, isEditing, onToggle, onRemove }: ChecklistRowProps) {
  return (
    <View style={styles.row}>
      <Pressable
        accessibilityRole="checkbox"
        accessibilityState={{ checked: item.isChecked }}
        hitSlop={spacing.sm}
        onPress={() => onToggle(item.id)}
        style={styles.pressableArea}
      >
        <View style={[styles.checkbox, item.isChecked && styles.checkedBox]}>
          {item.isChecked && <Ionicons color={colors.surface} name="checkmark" size={13} />}
        </View>
        <Text style={[styles.label, item.isChecked && styles.checkedLabel]}>{item.label}</Text>
      </Pressable>

      {isEditing && (
        <Pressable
          accessibilityLabel={`${item.label} 삭제`}
          accessibilityRole="button"
          hitSlop={spacing.sm}
          onPress={() => onRemove(item.id)}
        >
          <Ionicons color={colors.error} name="remove-circle-outline" size={19} />
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm - 2,
  },
  pressableArea: {
    alignItems: 'center',
    flex: 1,
    flexDirection: 'row',
    gap: spacing.sm + 4,
  },
  checkbox: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.sm - 1,
    borderWidth: 1.8,
    height: 21,
    justifyContent: 'center',
    width: 21,
  },
  checkedBox: {
    backgroundColor: colors.sea,
    borderColor: colors.sea,
  },
  label: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.label.fontSize + 1,
    fontWeight: typography.label.fontWeight,
  },
  checkedLabel: {
    color: colors.textTertiary,
    textDecorationLine: 'line-through',
  },
});
