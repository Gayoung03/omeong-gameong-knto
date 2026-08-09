import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors } from '@/src/theme';

type AuthHeaderProps = {
  title?: string;
  onBack: () => void;
  actionLabel?: string;
  onAction?: () => void;
};

export function AuthHeader({ title, onBack, actionLabel, onAction }: AuthHeaderProps) {
  return (
    <View style={styles.container}>
      <Pressable
        accessibilityLabel="뒤로가기"
        hitSlop={12}
        onPress={onBack}
        style={({ pressed }) => [styles.iconButton, pressed && styles.pressed]}
      >
        <Ionicons color={colors.textPrimary} name="arrow-back" size={25} />
      </Pressable>
      <Text numberOfLines={1} style={styles.title}>
        {title}
      </Text>
      {actionLabel && onAction ? (
        <Pressable hitSlop={10} onPress={onAction}>
          <Text style={styles.action}>{actionLabel}</Text>
        </Pressable>
      ) : (
        <View style={styles.iconButton} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    flexDirection: 'row',
    height: 52,
    justifyContent: 'space-between',
  },
  iconButton: {
    alignItems: 'center',
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  pressed: {
    opacity: 0.55,
  },
  title: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: 18,
    fontWeight: '800',
    textAlign: 'center',
  },
  action: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: '700',
  },
});

