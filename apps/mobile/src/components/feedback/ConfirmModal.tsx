import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, overlayColors, radius, shadow, spacing, typography } from '@/src/theme';

type ConfirmModalProps = {
  visible: boolean;
  title: string;
  description?: string;
  /** 본문 아래 작은 회색 한 줄. 오해를 미리 푸는 데 쓴다. */
  note?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** 되돌릴 수 없는 동작이면 'destructive'. 확인 버튼이 빨개진다. */
  tone?: 'default' | 'destructive';
  /** 처리 중이면 버튼을 잠근다. */
  isBusy?: boolean;
  busyLabel?: string;
  onCancel: () => void;
  onConfirm: () => void;
};

/**
 * 예/아니오를 묻는 공용 확인 창.
 *
 * **`Alert.alert` 을 쓰지 않는다.** Alert 은 웹에서 아예 뜨지 않아,
 * 확인을 받아야 하는 동작이 조용히 실패하거나(삭제가 안 됨) 확인 없이
 * 지나간 것처럼 보인다. 이 앱은 앱 스토어 승인이 늦어질 경우 **웹으로 심사**를
 * 받을 수 있어 웹에서 안 되는 확인 창을 남겨둘 수 없다.
 *
 * 안내만 하고 답을 받을 필요가 없으면 이걸 쓰지 말고 화면 안에 문구로 둔다.
 */
export function ConfirmModal({
  visible,
  title,
  description,
  note,
  confirmLabel = '확인',
  cancelLabel = '취소',
  tone = 'default',
  isBusy,
  busyLabel,
  onCancel,
  onConfirm,
}: ConfirmModalProps) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onCancel}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      <View style={styles.overlay}>
        <Pressable accessibilityLabel={cancelLabel} onPress={onCancel} style={styles.backdrop} />
        <View accessibilityViewIsModal style={[styles.card, shadow.sm]}>
          <Text style={styles.title}>{title}</Text>
          {description && <Text style={styles.description}>{description}</Text>}
          {note && <Text style={styles.note}>{note}</Text>}

          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              disabled={isBusy}
              onPress={onCancel}
              style={[styles.button, styles.cancelButton]}
            >
              <Text style={styles.cancelLabel}>{cancelLabel}</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              disabled={isBusy}
              onPress={onConfirm}
              style={[
                styles.button,
                tone === 'destructive' ? styles.destructiveButton : styles.confirmButton,
                isBusy && styles.buttonBusy,
              ]}
            >
              <Text style={styles.confirmLabel}>
                {isBusy ? (busyLabel ?? '처리 중...') : confirmLabel}
              </Text>
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
  buttonBusy: {
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
    backgroundColor: colors.primary,
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
  destructiveButton: {
    backgroundColor: colors.error,
  },
  note: {
    color: colors.textTertiary,
    fontSize: typography.caption.fontSize,
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
