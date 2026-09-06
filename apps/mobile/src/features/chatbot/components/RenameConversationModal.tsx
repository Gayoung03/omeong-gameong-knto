import { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { colors, overlayColors, radius, shadow, spacing, typography } from '@/src/theme';

import { useRenameConversation } from '../hooks/useConversations';
import type { ConversationSummary } from '../types/chatbot';
import { conversationErrorText } from '../utils/conversationError';

/** 서버 `ConversationUpdate.title` 의 상한과 같다. */
const TITLE_MAX_LENGTH = 150;

type Props = {
  /** `null` 이면 닫힌 상태다. */
  conversation: ConversationSummary | null;
  onClose: () => void;
};

/**
 * 대화 이름 바꾸기.
 *
 * 서버가 짓는 제목은 **첫 질문 30자**라, "안녕" 같은 짧은 첫 질문이면 목록이
 * "안녕"이 된다. 사용자가 직접 고칠 수 있어야 목록이 쓸모를 갖는다.
 *
 * `ChatbotScreen` 이 사이드바와 **형제로** 띄운다 — `Modal` 안에 `Modal` 을
 * 겹치면 플랫폼마다 층 순서가 달라진다.
 */
export function RenameConversationModal({ conversation, onClose }: Props) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onClose}
      statusBarTranslucent
      transparent
      visible={conversation !== null}
    >
      {/*
        입력 초기값을 `useEffect` + `setState` 로 넣으면 ESLint
        `react-hooks/set-state-in-effect` 에 걸린다. 자식을 따로 두면 열릴 때마다
        새로 마운트되면서 `useState` 초기값이 곧 그 대화의 제목이 된다.
      */}
      {conversation ? <RenameForm conversation={conversation} onClose={onClose} /> : null}
    </Modal>
  );
}

function RenameForm({
  conversation,
  onClose,
}: {
  conversation: ConversationSummary;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(conversation.title ?? '');
  const rename = useRenameConversation();

  const trimmed = title.trim();
  const canSave = trimmed.length > 0 && !rename.isPending;

  const handleSave = () => {
    if (!canSave) return;
    rename.mutate({ conversationId: conversation.id, title: trimmed }, { onSuccess: onClose });
  };

  return (
    <View style={styles.overlay}>
      <Pressable accessibilityLabel="취소" onPress={onClose} style={styles.backdrop} />
      <View accessibilityViewIsModal style={[styles.card, shadow.sm]}>
        <Text style={styles.title}>대화 이름 바꾸기</Text>
        <TextInput
          accessibilityLabel="대화 이름"
          autoFocus
          maxLength={TITLE_MAX_LENGTH}
          onChangeText={setTitle}
          onSubmitEditing={handleSave}
          placeholder="대화 이름을 입력하세요"
          placeholderTextColor={colors.textTertiary}
          returnKeyType="done"
          style={styles.input}
          value={title}
        />

        {rename.isError ? (
          <Text style={styles.errorText}>{conversationErrorText(rename.error)}</Text>
        ) : null}

        <View style={styles.actions}>
          <Pressable
            accessibilityRole="button"
            disabled={rename.isPending}
            onPress={onClose}
            style={({ pressed }) => [styles.button, styles.cancelButton, pressed && styles.pressed]}
          >
            <Text style={styles.cancelLabel}>취소</Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ disabled: !canSave }}
            disabled={!canSave}
            onPress={handleSave}
            style={({ pressed }) => [
              styles.button,
              styles.saveButton,
              !canSave && styles.saveButtonDisabled,
              pressed && styles.pressed,
            ]}
          >
            <Text style={styles.saveLabel}>{rename.isPending ? '저장 중...' : '저장'}</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  backdrop: {
    bottom: 0,
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  button: {
    alignItems: 'center',
    borderRadius: radius.sm,
    flex: 1,
    justifyContent: 'center',
    minHeight: 46,
  },
  cancelButton: {
    backgroundColor: colors.neutralGray,
  },
  cancelLabel: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    maxWidth: 360,
    padding: spacing.lg,
    width: '88%',
  },
  errorText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    marginTop: spacing.sm,
  },
  input: {
    borderColor: colors.divider,
    borderRadius: radius.sm,
    borderWidth: 1,
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    marginTop: spacing.md,
    minHeight: 46,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.sm,
  },
  overlay: {
    alignItems: 'center',
    backgroundColor: overlayColors.dim,
    flex: 1,
    justifyContent: 'center',
    padding: spacing.md,
  },
  pressed: {
    opacity: 0.68,
  },
  saveButton: {
    backgroundColor: colors.primary,
  },
  saveButtonDisabled: {
    backgroundColor: colors.divider,
  },
  saveLabel: {
    color: colors.surface,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
    textAlign: 'center',
  },
});
