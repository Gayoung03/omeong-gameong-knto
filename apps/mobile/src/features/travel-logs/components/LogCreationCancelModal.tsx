import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, shadow, spacing, typography } from '@/src/theme';

type Props = {
  onCancelCreation: () => void;
  onContinue: () => void;
  visible: boolean;
};

export function LogCreationCancelModal({ onCancelCreation, onContinue, visible }: Props) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onContinue}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      <View style={styles.overlay}>
        <Pressable accessibilityLabel="계속 작성" onPress={onContinue} style={styles.backdrop} />
        <View accessibilityViewIsModal style={[styles.card, shadow.sm]}>
          <Text style={styles.title}>로그 작성을 취소할까요?</Text>
          <Text style={styles.description}>이 페이지에서 나가면 작성 중인 내용이 모두 사라져요.</Text>
          <View style={styles.actions}>
            <Pressable accessibilityRole="button" onPress={onContinue} style={[styles.button, styles.continueButton]}>
              <Text style={styles.continueLabel}>계속 작성</Text>
            </Pressable>
            <Pressable accessibilityRole="button" onPress={onCancelCreation} style={[styles.button, styles.cancelButton]}>
              <Text style={styles.cancelLabel}>작성 취소</Text>
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
  cancelButton: { backgroundColor: colors.error },
  cancelLabel: { color: colors.surface, fontSize: 14, fontWeight: '700' },
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, maxWidth: 360, padding: spacing.lg, width: '88%' },
  continueButton: { backgroundColor: colors.neutralGray },
  continueLabel: { color: colors.textPrimary, fontSize: 14, fontWeight: '700' },
  description: { color: colors.textSecondary, fontSize: 14, lineHeight: 21, marginTop: spacing.sm, textAlign: 'center' },
  overlay: { alignItems: 'center', backgroundColor: 'rgba(0, 0, 0, 0.48)', flex: 1, justifyContent: 'center', padding: spacing.md },
  title: { color: colors.textPrimary, fontSize: typography.body.fontSize + 1, fontWeight: '700', textAlign: 'center' },
});
