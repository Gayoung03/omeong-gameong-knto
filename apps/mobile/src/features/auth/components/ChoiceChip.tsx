import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text } from 'react-native';

import { colors } from '@/src/theme';

type ChoiceChipProps = {
  label: string;
  selected: boolean;
  onPress: () => void;
  icon?: keyof typeof Ionicons.glyphMap;
  grow?: boolean;
};

export function ChoiceChip({ label, selected, onPress, icon, grow = false }: ChoiceChipProps) {
  return (
    <Pressable
      accessibilityState={{ selected }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        grow && styles.grow,
        selected && styles.selected,
        pressed && styles.pressed,
      ]}
    >
      {icon && <Ionicons color={selected ? '#18967C' : '#55504D'} name={icon} size={20} />}
      <Text style={[styles.label, selected && styles.labelSelected]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: '#E6E4E2',
    borderRadius: 13,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 7,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: 15,
  },
  grow: {
    flex: 1,
  },
  selected: {
    backgroundColor: '#EEFBF7',
    borderColor: '#45BFA4',
  },
  pressed: {
    opacity: 0.72,
  },
  label: {
    color: '#4F4B48',
    fontSize: 14,
    fontWeight: '700',
  },
  labelSelected: {
    color: '#168F77',
  },
});

