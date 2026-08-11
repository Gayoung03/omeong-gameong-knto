import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text } from 'react-native';

import { colors } from '@/src/theme';

type PrimaryButtonProps = {
  label: string;
  onPress: () => void;
  icon?: keyof typeof Ionicons.glyphMap;
};

export function PrimaryButton({ label, onPress, icon }: PrimaryButtonProps) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}
    >
      <Text style={styles.label}>{label}</Text>
      {icon && <Ionicons color={colors.surface} name={icon} size={22} />}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: 15,
    flexDirection: 'row',
    justifyContent: 'center',
    minHeight: 58,
    paddingHorizontal: 20,
  },
  buttonPressed: {
    opacity: 0.82,
    transform: [{ scale: 0.995 }],
  },
  label: {
    color: colors.surface,
    flex: 1,
    fontSize: 17,
    fontWeight: '800',
    textAlign: 'center',
  },
});

