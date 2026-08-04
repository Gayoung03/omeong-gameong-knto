import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { MemoDraft } from '../hooks/useTripMemos';

type MemoEditModalProps = {
  dayLabel: string;
  initialDraft: MemoDraft;
  onClose: () => void;
  onSubmit: (draft: MemoDraft) => void;
};

export function MemoEditModal({ dayLabel, initialDraft, onClose, onSubmit }: MemoEditModalProps) {
  const [title, setTitle] = useState(initialDraft.title);
  const [content, setContent] = useState(initialDraft.content);

  const handlePressSave = () => {
    onSubmit({ title, content });
    onClose();
  };

  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.backdrop}
      >
        <Pressable onPress={onClose} style={styles.backdropArea} />

        <View style={styles.sheet}>
          <View style={styles.grip} />

          <View style={styles.header}>
            <Pressable accessibilityRole="button" hitSlop={spacing.sm} onPress={onClose}>
              <Text style={styles.cancelText}>취소</Text>
            </Pressable>
            <Text style={styles.headerTitle}>{dayLabel} 메모</Text>
            <Pressable accessibilityRole="button" hitSlop={spacing.sm} onPress={handlePressSave}>
              <Text style={styles.saveText}>저장</Text>
            </Pressable>
          </View>

          <TextInput
            onChangeText={setTitle}
            placeholder="제목 (예: 협재 → 애월 서쪽 코스)"
            placeholderTextColor={colors.textTertiary}
            style={styles.titleInput}
            value={title}
          />

          <TextInput
            multiline
            onChangeText={setContent}
            placeholder="기억해둘 내용을 자유롭게 적어보세요"
            placeholderTextColor={colors.textTertiary}
            style={styles.contentInput}
            textAlignVertical="top"
            value={content}
          />
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: 'rgba(30, 28, 25, 0.45)',
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdropArea: {
    flex: 1,
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl + 4,
    borderTopRightRadius: radius.xl + 4,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  grip: {
    alignSelf: 'center',
    backgroundColor: colors.border,
    borderRadius: radius.sm,
    height: 4,
    marginBottom: spacing.md,
    width: 40,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingBottom: spacing.md,
  },
  headerTitle: {
    color: colors.basalt,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  cancelText: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
  },
  saveText: {
    color: colors.primary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  titleInput: {
    backgroundColor: colors.background,
    borderRadius: radius.md,
    color: colors.textPrimary,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  contentInput: {
    backgroundColor: colors.background,
    borderRadius: radius.md,
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    lineHeight: 21,
    marginTop: spacing.sm,
    minHeight: 140,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
});
