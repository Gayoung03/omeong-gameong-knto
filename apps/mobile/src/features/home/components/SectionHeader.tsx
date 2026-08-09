import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors } from '@/src/theme';

type SectionHeaderProps = {
  title: string;
  actionLabel?: string;
  onPressAction?: () => void;
};

export function SectionHeader({ title, actionLabel, onPressAction }: SectionHeaderProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      {actionLabel && onPressAction ? (
        <Pressable
          accessibilityRole="button"
          hitSlop={10}
          onPress={onPressAction}
          style={({ pressed }) => pressed && styles.pressed}
        >
          <Text style={styles.action}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    color: colors.textPrimary,
    fontSize: 18,
    fontWeight: '800',
    letterSpacing: -0.4,
  },
  action: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
  },
  pressed: {
    opacity: 0.55,
  },
});
