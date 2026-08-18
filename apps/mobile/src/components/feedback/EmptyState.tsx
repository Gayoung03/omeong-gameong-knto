import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type EmptyStateProps = {
  /** 액션 버튼 문구. `onPressAction` 과 함께 넘길 때만 버튼이 보인다. */
  actionLabel?: string;
  description: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPressAction?: () => void;
  title: string;
};

/** 목록이 비어 있을 때 화면 가운데에 놓는 안내. */
export function EmptyState({
  actionLabel,
  description,
  icon,
  onPressAction,
  title,
}: EmptyStateProps) {
  return (
    <View style={styles.container}>
      <View style={styles.iconCircle}>
        <Ionicons color={colors.primary} name={icon} size={30} />
      </View>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.description}>{description}</Text>

      {actionLabel && onPressAction ? (
        <Pressable
          accessibilityRole="button"
          onPress={onPressAction}
          style={({ pressed }) => [styles.action, pressed && styles.pressed]}
        >
          <Text style={styles.actionLabel}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  action: {
    backgroundColor: colors.primary,
    borderRadius: radius.full,
    marginTop: spacing.lg,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm + 2,
  },
  actionLabel: {
    color: colors.surface,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  container: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    lineHeight: 21,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  iconCircle: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    height: 64,
    justifyContent: 'center',
    marginBottom: spacing.md,
    width: 64,
  },
  pressed: {
    opacity: 0.75,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: '700',
    textAlign: 'center',
  },
});
