import type { PropsWithChildren } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { colors, radius, shadow, spacing } from '@/src/theme';

type CardProps = PropsWithChildren<{
  style?: StyleProp<ViewStyle>;
  padding?: keyof typeof spacing;
}>;

export function Card({ children, style, padding = 'md' }: CardProps) {
  return <View style={[styles.card, { padding: spacing[padding] }, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    ...shadow.sm,
  },
});
