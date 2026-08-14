import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

type KeywordEditorProps = {
  keywords: string[];
  onAdd: (keyword: string) => void;
  onRemove: (keyword: string) => void;
};

export function KeywordEditor({ keywords, onAdd, onRemove }: KeywordEditorProps) {
  const [newKeyword, setNewKeyword] = useState('');

  const handleSubmit = () => {
    onAdd(newKeyword);
    setNewKeyword('');
  };

  return (
    <View style={styles.container}>
      <View style={styles.chipRow}>
        {keywords.map((keyword) => (
          <View key={keyword} style={styles.chip}>
            <Text style={styles.chipText}>{keyword}</Text>
            <Pressable
              accessibilityLabel={`${keyword} 삭제`}
              accessibilityRole="button"
              hitSlop={spacing.xs}
              onPress={() => onRemove(keyword)}
            >
              <Ionicons color={colors.primary} name="close" size={12} />
            </Pressable>
          </View>
        ))}
      </View>

      <View style={styles.inputRow}>
        <TextInput
          onChangeText={setNewKeyword}
          onSubmitEditing={handleSubmit}
          placeholder="키워드 추가"
          placeholderTextColor={colors.textTertiary}
          returnKeyType="done"
          style={styles.input}
          value={newKeyword}
        />
        <Pressable accessibilityRole="button" hitSlop={spacing.xs} onPress={handleSubmit}>
          <Text style={styles.addText}>추가</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.xs + 2,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs + 2,
  },
  chip: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    flexDirection: 'row',
    gap: spacing.xs,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: 4,
  },
  chipText: {
    color: colors.primary,
    fontSize: typography.micro.fontSize,
    fontWeight: '700',
  },
  inputRow: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.sm,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs + 2,
  },
  input: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.caption.fontSize + 1,
    padding: 0,
  },
  addText: {
    color: colors.primary,
    fontSize: typography.micro.fontSize + 1,
    fontWeight: '700',
  },
});
