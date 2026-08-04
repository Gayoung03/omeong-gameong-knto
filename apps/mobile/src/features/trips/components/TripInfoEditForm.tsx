import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { useTripInfoForm } from '../hooks/useTripInfoForm';
import type { TripTransport } from '../types/trip';
import { DateRangeField } from './DateRangeField';
import { KeywordEditor } from './KeywordEditor';
import { PetEditRow } from './PetEditRow';
import { SelectChips, type SelectChipOption } from './SelectChips';

const TRANSPORT_OPTIONS: SelectChipOption<TripTransport>[] = [
  { value: 'rentalCar', label: '렌터카' },
  { value: 'ownCar', label: '자차' },
  { value: 'publicTransport', label: '대중교통' },
  { value: 'walk', label: '도보' },
];

type TripInfoForm = ReturnType<typeof useTripInfoForm>;

type TripInfoEditFormProps = {
  form: TripInfoForm;
};

type FieldProps = {
  label: string;
  children: React.ReactNode;
};

function Field({ label, children }: FieldProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      {children}
    </View>
  );
}

export function TripInfoEditForm({ form }: TripInfoEditFormProps) {
  const {
    draft,
    updateField,
    updateDateRange,
    updatePet,
    addPet,
    removePet,
    addKeyword,
    removeKeyword,
  } = form;

  return (
    <View style={styles.card}>
      <Field label="여행 이름">
        <TextInput
          onChangeText={(title) => updateField('title', title)}
          placeholder="여행 이름을 입력하세요"
          placeholderTextColor={colors.textTertiary}
          style={styles.input}
          value={draft.title}
        />
      </Field>

      <Field label="여행 기간">
        <DateRangeField
          endDate={draft.endDate}
          onChangeRange={updateDateRange}
          startDate={draft.startDate}
        />
      </Field>

      <Field label="이동 수단">
        <SelectChips
          onSelect={(transport) => updateField('transport', transport)}
          options={TRANSPORT_OPTIONS}
          selectedValue={draft.transport}
        />
      </Field>

      <Field label="반려동물">
        <View style={styles.petList}>
          {draft.pets.map((pet) => (
            <PetEditRow
              canRemove={draft.pets.length > 1}
              key={pet.id}
              onChange={updatePet}
              onRemove={removePet}
              pet={pet}
            />
          ))}

          <Pressable accessibilityRole="button" onPress={addPet} style={styles.addPetButton}>
            <Text style={styles.addPetText}>＋ 반려동물 추가</Text>
          </Pressable>
        </View>
      </Field>

      <Field label="숙소">
        <TextInput
          onChangeText={(value) => updateField('accommodationSummary', value)}
          placeholder="예: 성산 숙소 2곳"
          placeholderTextColor={colors.textTertiary}
          style={styles.input}
          value={draft.accommodationSummary}
        />
      </Field>

      <Field label="여행 스타일">
        <TextInput
          onChangeText={(value) => updateField('travelStyle', value)}
          placeholder="예: 여유로운 힐링 여행"
          placeholderTextColor={colors.textTertiary}
          style={styles.input}
          value={draft.travelStyle}
        />
      </Field>

      <Field label="선호 키워드">
        <KeywordEditor keywords={draft.styleKeywords} onAdd={addKeyword} onRemove={removeKeyword} />
      </Field>

      <Field label="메모">
        <TextInput
          multiline
          onChangeText={(value) => updateField('memo', value)}
          placeholder="이번 여행에서 기억해둘 점을 적어보세요"
          placeholderTextColor={colors.textTertiary}
          style={[styles.input, styles.memoInput]}
          textAlignVertical="top"
          value={draft.memo}
        />
      </Field>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg + 2,
    borderWidth: 1,
    gap: spacing.md,
    marginHorizontal: spacing.lg - 2,
    marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
  },
  field: {
    gap: spacing.xs + 2,
  },
  fieldLabel: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize + 1,
    fontWeight: '700',
  },
  input: {
    backgroundColor: colors.background,
    borderRadius: radius.sm,
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.xs + 4,
  },
  memoInput: {
    fontWeight: '400',
    lineHeight: 21,
    minHeight: 96,
  },
  petList: {
    gap: spacing.sm + 2,
  },
  addPetButton: {
    alignItems: 'center',
    borderColor: colors.border,
    borderRadius: radius.sm,
    borderStyle: 'dashed',
    borderWidth: 1.5,
    paddingVertical: spacing.xs + 4,
  },
  addPetText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
});
