import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import { useChecklist } from '../hooks/useChecklist';
import { CHECKLIST_CATEGORY_LABELS } from '../mocks/checklist.mock';
import { ChecklistProgress } from './ChecklistProgress';
import { ChecklistRow } from './ChecklistRow';

export function ChecklistTab() {
  const { sections, totalCount, checkedCount, progressRate, toggleItem, addItem, removeItem } =
    useChecklist();

  const [isEditing, setIsEditing] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [newItemLabel, setNewItemLabel] = useState('');

  const handlePressEdit = () => {
    setIsEditing((previous) => !previous);
  };

  const handleSubmitNewItem = () => {
    addItem(newItemLabel);
    setNewItemLabel('');
    setIsAdding(false);
  };

  const handleCancelAdd = () => {
    setNewItemLabel('');
    setIsAdding(false);
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>제주 여행 체크리스트</Text>
        <Pressable accessibilityRole="button" hitSlop={spacing.sm} onPress={handlePressEdit}>
          <Text style={[styles.editText, isEditing && styles.editingText]}>
            {isEditing ? '완료' : '편집'}
          </Text>
        </Pressable>
      </View>

      <ChecklistProgress
        checkedCount={checkedCount}
        progressRate={progressRate}
        totalCount={totalCount}
      />

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {sections.map((section) => (
          <View key={section.category}>
            <Text style={styles.sectionTitle}>{CHECKLIST_CATEGORY_LABELS[section.category]}</Text>
            {section.items.map((item) => (
              <ChecklistRow
                isEditing={isEditing}
                item={item}
                key={item.id}
                onRemove={removeItem}
                onToggle={toggleItem}
              />
            ))}
          </View>
        ))}

        {isAdding ? (
          <View style={styles.addForm}>
            <TextInput
              autoFocus
              onChangeText={setNewItemLabel}
              onSubmitEditing={handleSubmitNewItem}
              placeholder="추가할 준비물을 입력하세요"
              placeholderTextColor={colors.textTertiary}
              returnKeyType="done"
              style={styles.addInput}
              value={newItemLabel}
            />
            <Pressable accessibilityRole="button" onPress={handleCancelAdd}>
              <Text style={styles.cancelText}>취소</Text>
            </Pressable>
            <Pressable accessibilityRole="button" onPress={handleSubmitNewItem}>
              <Text style={styles.submitText}>추가</Text>
            </Pressable>
          </View>
        ) : (
          <Pressable
            accessibilityRole="button"
            onPress={() => setIsAdding(true)}
            style={styles.addButton}
          >
            <Text style={styles.addButtonText}>＋ 항목 추가</Text>
          </Pressable>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg - 2,
    paddingTop: spacing.md,
  },
  title: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: typography.sectionTitle.fontWeight,
  },
  editText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  editingText: {
    color: colors.primary,
    fontWeight: '700',
  },
  scrollContent: {
    paddingBottom: spacing.xl,
    paddingTop: spacing.sm,
  },
  sectionTitle: {
    color: colors.leaf,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.xs,
  },
  addButton: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md + 2,
    borderStyle: 'dashed',
    borderWidth: 1.5,
    marginHorizontal: spacing.lg - 2,
    marginTop: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  addButtonText: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  addForm: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.primary,
    borderRadius: radius.md + 2,
    borderWidth: 1.5,
    flexDirection: 'row',
    gap: spacing.sm,
    marginHorizontal: spacing.lg - 2,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  addInput: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.label.fontSize + 1,
    padding: 0,
  },
  cancelText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  submitText: {
    color: colors.primary,
    fontSize: typography.caption.fontSize,
    fontWeight: '700',
  },
});
