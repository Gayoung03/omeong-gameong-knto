import { StyleSheet, Text, TextInput, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { useTripInfoForm } from '../hooks/useTripInfoForm';
import { KeywordEditor } from './KeywordEditor';

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

/**
 * 여행 정보 편집 폼.
 *
 * **서버 `PATCH /routes` 가 받는 세 가지만 있다.** 기간·이동수단·반려동물·숙소·
 * 여행스타일 칸은 저장이 안 돼서 뺐다 — 자세한 사정은 `hooks/useTripInfoForm.ts` 주석에.
 * 읽기 화면(`TripInfoView`)에서는 그대로 다 보인다.
 */
export function TripInfoEditForm({ form }: TripInfoEditFormProps) {
  const { draft, updateField, addKeyword, removeKeyword } = form;

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
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.sm,
    borderWidth: 1,
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
