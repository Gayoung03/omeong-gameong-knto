import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, shadow, spacing, typography } from '@/src/theme';

type Props = {
  onDiscard: () => void;
  onContinue: () => void;
  visible: boolean;
  description?: string;
};

export function DiscardChangesModal({
  onDiscard,
  onContinue,
  visible,
  description = '프로필 정보의 변경 사항이 저장되지 않아요.',
}: Props) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onContinue}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      <View style={styles.overlay}>
        <Pressable accessibilityLabel="계속 수정" onPress={onContinue} style={styles.backdrop} />
        <View accessibilityViewIsModal style={[styles.card, shadow.sm]}>
          <Text style={styles.title}>변경사항을 저장하지 않고 나갈까요?</Text>
          <Text style={styles.description}>{description}</Text>
          <View style={styles.actions}>
            <Pressable accessibilityRole="button" onPress={onContinue} style={[styles.button, styles.continueButton]}>
              <Text style={styles.continueLabel}>계속 수정</Text>
            </Pressable>
            <Pressable accessibilityRole="button" onPress={onDiscard} style={[styles.button, styles.discardButton]}>
              <Text style={styles.discardLabel}>나가기</Text>
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
  card: { backgroundColor: colors.surface, borderRadius: radius.lg, maxWidth: 360, padding: spacing.lg, width: '88%' },
  continueButton: { backgroundColor: colors.neutralGray },
  continueLabel: { color: colors.textPrimary, fontSize: 14, fontWeight: '700' },
  description: { color: colors.textSecondary, fontSize: 14, lineHeight: 21, marginTop: spacing.sm, textAlign: 'center' },
  discardButton: { backgroundColor: colors.error },
  discardLabel: { color: colors.surface, fontSize: 14, fontWeight: '700' },
  overlay: { alignItems: 'center', backgroundColor: 'rgba(0, 0, 0, 0.48)', flex: 1, justifyContent: 'center', padding: spacing.md },
  title: { color: colors.textPrimary, fontSize: typography.body.fontSize + 1, fontWeight: '700', textAlign: 'center' },
});
