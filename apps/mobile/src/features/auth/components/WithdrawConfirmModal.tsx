import { ActivityIndicator, Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, overlayColors, radius, shadow, spacing, typography } from '@/src/theme';

type Props = {
  visible: boolean;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

/** 탈퇴 직전 마지막 확인. 여기서 확인을 눌러야 실제 요청이 나간다. */
export function WithdrawConfirmModal({ visible, isPending, onCancel, onConfirm }: Props) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onCancel}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      <View style={styles.overlay}>
        <Pressable
          accessibilityLabel="취소"
          disabled={isPending}
          onPress={onCancel}
          style={styles.backdrop}
        />
        <View accessibilityViewIsModal style={[styles.card, shadow.sm]}>
          <Text style={styles.title}>회원 탈퇴를 진행할까요?</Text>
          <Text style={styles.description}>
            삭제된 데이터는 복구할 수 없으며,{'\n'}동일한 이메일로 다시 가입할 수 없습니다.
          </Text>
          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              disabled={isPending}
              onPress={onCancel}
              style={[styles.button, styles.cancelButton]}
            >
              <Text style={styles.cancelLabel}>취소</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: isPending }}
              disabled={isPending}
              onPress={onConfirm}
              style={[styles.button, styles.confirmButton, isPending && styles.confirmButtonBusy]}
            >
              {isPending ? (
                <ActivityIndicator color={colors.surface} size="small" />
              ) : (
                <Text style={styles.confirmLabel}>탈퇴하기</Text>
              )}
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md },
  backdrop: { bottom: 0, left: 0, position: 'absolute', right: 0, top: 0 },
  button: { alignItems: 'center', borderRadius: radius.sm, flex: 1, justifyContent: 'center', minHeight: 48, paddingHorizontal: spacing.sm },
  cancelButton: { backgroundColor: colors.neutralGray },
  cancelLabel: { color: colors.textPrimary, fontSize: 14, fontWeight: '700' },
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, maxWidth: 360, padding: spacing.lg, width: '88%' },
  confirmButton: { backgroundColor: colors.error },
  confirmButtonBusy: { opacity: 0.6 },
  confirmLabel: { color: colors.surface, fontSize: 14, fontWeight: '700' },
  description: { color: colors.textSecondary, fontSize: 14, lineHeight: 21, marginTop: spacing.sm, textAlign: 'center' },
  overlay: { alignItems: 'center', backgroundColor: overlayColors.dim, flex: 1, justifyContent: 'center', padding: spacing.md },
  title: { color: colors.textPrimary, fontSize: typography.body.fontSize + 1, fontWeight: '700', textAlign: 'center' },
});
