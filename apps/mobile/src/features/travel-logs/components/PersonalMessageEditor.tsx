import { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { Button } from '@/src/components/ui/Button';
import { colors, radius, spacing, typography } from '@/src/theme';

const MAX_LENGTH = 80;

type PersonalMessageEditorProps = {
  initialValue: string;
  isSaving: boolean;
  onSave: (message: string | null) => void;
  onCancel: () => void;
};

/** 팝업 뒷면 내부에서 나의 한 줄을 편집하는 작은 폼. 공백만 남으면 빈 값으로 저장한다. */
export function PersonalMessageEditor({
  initialValue,
  isSaving,
  onSave,
  onCancel,
}: PersonalMessageEditorProps) {
  const [draft, setDraft] = useState(initialValue);

  const handleSave = () => {
    const trimmed = draft.trim();
    onSave(trimmed.length > 0 ? trimmed : null);
  };

  return (
    <View style={styles.container}>
      <TextInput
        maxLength={MAX_LENGTH}
        multiline
        onChangeText={setDraft}
        placeholder="이 순간을 한 줄로 남겨보세요"
        placeholderTextColor={colors.textSecondary}
        style={styles.input}
        value={draft}
      />
      <Text style={styles.counter}>
        {draft.length}/{MAX_LENGTH}
      </Text>

      <View style={styles.actions}>
        <View style={styles.actionButton}>
          <Button label="취소" onPress={onCancel} variant="outline" />
        </View>
        <View style={styles.actionButton}>
          <Button label={isSaving ? '저장 중...' : '저장'} onPress={handleSave} variant="primary" />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  actionButton: {
    flex: 1,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  container: {
    flex: 1,
    gap: spacing.sm,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  counter: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 4,
    textAlign: 'right',
  },
  input: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.textPrimary,
    fontSize: typography.body.fontSize - 1,
    maxHeight: 100,
    minHeight: 72,
    padding: spacing.sm,
    textAlignVertical: 'top',
  },
});
