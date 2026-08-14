import { Pressable, StyleSheet, Text } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type ButtonVariant = 'primary' | 'outline';
type ButtonSize = 'sm' | 'md';

type ButtonProps = {
  label: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
};

export function Button({ label, onPress, variant = 'primary', size = 'md', disabled = false }: ButtonProps) {
  const isOutline = variant === 'outline';

  return (
    <Pressable
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={disabled ? undefined : onPress}
      style={[
        styles.base,
        size === 'sm' ? styles.sizeSm : styles.sizeMd,
        isOutline ? styles.variantOutline : styles.variantPrimary,
        disabled && (isOutline ? styles.disabledOutline : styles.disabledPrimary),
      ]}
    >
      <Text
        style={[
          styles.label,
          isOutline ? styles.labelOutline : styles.labelPrimary,
          disabled && styles.labelDisabled,
        ]}
      >
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    borderRadius: radius.sm,
    justifyContent: 'center',
  },
  disabledOutline: {
    backgroundColor: colors.neutralGray,
    borderColor: colors.border,
  },
  disabledPrimary: {
    backgroundColor: colors.neutralGray,
  },
  label: {
    fontSize: typography.body.fontSize,
    fontWeight: typography.body.fontWeight,
  },
  labelDisabled: {
    color: colors.textSecondary,
  },
  labelOutline: {
    color: colors.primary,
  },
  labelPrimary: {
    color: colors.surface,
  },
  sizeMd: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  sizeSm: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  variantOutline: {
    backgroundColor: colors.surface,
    borderColor: colors.primary,
    borderWidth: 1,
  },
  variantPrimary: {
    backgroundColor: colors.primary,
  },
});
