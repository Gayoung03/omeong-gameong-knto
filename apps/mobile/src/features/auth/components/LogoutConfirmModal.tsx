import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, shadow, spacing, typography } from '@/src/theme';

type Props = {
  visible: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function LogoutConfirmModal({ visible, onCancel, onConfirm }: Props) {
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
          <Text style={styles.title}>로그아웃 할까요?</Text>
          <Text style={styles.description}>
            다시 로그인하면 언제든{'\n'}기존 여행 기록을 볼 수 있어요.
          </Text>
          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              onPress={onCancel}
              style={[styles.button, styles.cancelButton]}
            >
              <Text style={styles.cancelLabel}>취소</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={onConfirm}
              style={[styles.button, styles.confirmButton]}
            >
              <Text style={styles.confirmLabel}>로그아웃</Text>
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
  confirmLabel: { color: colors.surface, fontSize: 14, fontWeight: '700' },
  description: { color: colors.textSecondary, fontSize: 14, lineHeight: 21, marginTop: spacing.sm, textAlign: 'center' },
  overlay: { alignItems: 'center', backgroundColor: 'rgba(0, 0, 0, 0.48)', flex: 1, justifyContent: 'center', padding: spacing.md },
  title: { color: colors.textPrimary, fontSize: typography.body.fontSize + 1, fontWeight: '700', textAlign: 'center' },
});
