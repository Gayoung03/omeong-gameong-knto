import Ionicons from '@expo/vector-icons/Ionicons';
import type { ComponentProps } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type IoniconName = ComponentProps<typeof Ionicons>['name'];

type TripInfoRowProps = {
  iconName: IoniconName;
  iconBackgroundColor: string;
  iconColor: string;
  label: string;
  isFirst: boolean;
  children: React.ReactNode;
};

export function TripInfoRow({
  iconName,
  iconBackgroundColor,
  iconColor,
  label,
  isFirst,
  children,
}: TripInfoRowProps) {
  return (
    <View style={[styles.row, !isFirst && styles.dividedRow]}>
      <View style={[styles.iconBox, { backgroundColor: iconBackgroundColor }]}>
        <Ionicons color={iconColor} name={iconName} size={16} />
      </View>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.value}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm + 4,
    paddingVertical: spacing.md - 2,
  },
  dividedRow: {
    borderTopColor: colors.border,
    borderTopWidth: 1,
  },
  iconBox: {
    alignItems: 'center',
    borderRadius: radius.sm + 2,
    height: 34,
    justifyContent: 'center',
    width: 34,
  },
  label: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
    width: 72,
  },
  value: {
    flex: 1,
  },
});
