import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { TripPet } from '../types/trip';
import { SelectChips, type SelectChipOption } from './SelectChips';

type PetSizeType = TripPet['sizeType'];

const SIZE_OPTIONS: SelectChipOption<PetSizeType>[] = [
  { value: 'small', label: '소형견' },
  { value: 'medium', label: '중형견' },
  { value: 'large', label: '대형견' },
];

type PetEditRowProps = {
  pet: TripPet;
  canRemove: boolean;
  onChange: (petId: string, patch: Partial<Omit<TripPet, 'id'>>) => void;
  onRemove: (petId: string) => void;
};

export function PetEditRow({ pet, canRemove, onChange, onRemove }: PetEditRowProps) {
  const handleChangeCount = (delta: number) => {
    onChange(pet.id, { count: Math.max(1, pet.count + delta) });
  };

  return (
    <View style={styles.container}>
      <View style={styles.topRow}>
        <TextInput
          onChangeText={(name) => onChange(pet.id, { name })}
          placeholder="이름"
          placeholderTextColor={colors.textTertiary}
          style={styles.nameInput}
          value={pet.name}
        />

        <View style={styles.stepper}>
          <Pressable
            accessibilityLabel="마리 수 줄이기"
            accessibilityRole="button"
            hitSlop={spacing.xs}
            onPress={() => handleChangeCount(-1)}
            style={styles.stepperButton}
          >
            <Ionicons color={colors.textSecondary} name="remove" size={14} />
          </Pressable>
          <Text style={styles.countText}>{pet.count}</Text>
          <Pressable
            accessibilityLabel="마리 수 늘리기"
            accessibilityRole="button"
            hitSlop={spacing.xs}
            onPress={() => handleChangeCount(1)}
            style={styles.stepperButton}
          >
            <Ionicons color={colors.textSecondary} name="add" size={14} />
          </Pressable>
        </View>

        {canRemove && (
          <Pressable
            accessibilityLabel={`${pet.name || '반려동물'} 삭제`}
            accessibilityRole="button"
            hitSlop={spacing.xs}
            onPress={() => onRemove(pet.id)}
          >
            <Ionicons color={colors.error} name="close-circle-outline" size={19} />
          </Pressable>
        )}
      </View>

      <SelectChips
        onSelect={(sizeType) => onChange(pet.id, { sizeType })}
        options={SIZE_OPTIONS}
        selectedValue={pet.sizeType}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.xs + 2,
  },
  topRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
  },
  nameInput: {
    backgroundColor: colors.background,
    borderRadius: radius.sm,
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs + 3,
  },
  stepper: {
    alignItems: 'center',
    backgroundColor: colors.background,
    borderRadius: radius.full,
    flexDirection: 'row',
    gap: spacing.xs,
    paddingHorizontal: spacing.xs + 2,
    paddingVertical: 3,
  },
  stepperButton: {
    padding: 2,
  },
  countText: {
    color: colors.basalt,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
    minWidth: 14,
    textAlign: 'center',
  },
});
