import { StyleSheet, Switch, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/src/theme';

type Props = {
  label: string;
  value: boolean;
  onValueChange: (next: boolean) => void;
  disabled?: boolean;
};

export function NotificationSettingRow({ label, value, onValueChange, disabled = false }: Props) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Switch
        disabled={disabled}
        ios_backgroundColor={colors.border}
        onValueChange={onValueChange}
        thumbColor={colors.surface}
        trackColor={{ false: colors.border, true: colors.mintIcon }}
        value={value}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  label: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.body.fontSize,
  },
  row: {
    alignItems: 'center',
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: spacing.md,
    minHeight: 68,
  },
});
