import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, overlayColors, radius, shadow, spacing, typography } from '@/src/theme';

type Props = {
  visible: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  isDeleting?: boolean;
};

/**
 * 리뷰 삭제 확인.
 *
 * `Alert.alert` 을 쓰지 않는 이유 — 웹에서는 아예 뜨지 않아
 * 사용자가 확인 없이 지워지는 것처럼 느낀다. 되돌릴 수 없는 동작이라 더 그렇다.
 */
export function ReviewDeleteConfirmModal({ visible, onCancel, onConfirm, isDeleting }: Props) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onCancel}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      <View style={styles.overlay}>
        <Pressable accessibilityLabel="취소" onPress={onCancel} style={styles.backdrop} />
        <View accessibilityViewIsModal style={[styles.card, shadow.sm]}>
          <Text style={styles.title}>리뷰를 삭제할까요?</Text>
          <Text style={styles.description}>첨부한 사진도 함께 지워지고{'\n'}되돌릴 수 없어요.</Text>
          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              disabled={isDeleting}
              onPress={onCancel}
              style={[styles.button, styles.cancelButton]}
            >
              <Text style={styles.cancelLabel}>취소</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              disabled={isDeleting}
              onPress={onConfirm}
              style={[styles.button, styles.confirmButton, isDeleting && styles.buttonDisabled]}
            >
              <Text style={styles.confirmLabel}>{isDeleting ? '삭제 중...' : '삭제'}</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
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
    minHeight: 48,
    paddingHorizontal: spacing.sm,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  cancelButton: {
    backgroundColor: colors.neutralGray,
  },
  cancelLabel: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    maxWidth: 360,
    padding: spacing.lg,
    width: '88%',
  },
  confirmButton: {
    backgroundColor: colors.error,
  },
  confirmLabel: {
    color: colors.surface,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize + 1,
    lineHeight: 21,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  overlay: {
    alignItems: 'center',
    backgroundColor: overlayColors.dim,
    flex: 1,
    justifyContent: 'center',
    padding: spacing.md,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize + 1,
    fontWeight: '700',
    textAlign: 'center',
  },
});
