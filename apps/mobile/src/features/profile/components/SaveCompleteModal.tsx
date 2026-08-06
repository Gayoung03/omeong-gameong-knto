import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, shadow, spacing, typography } from '@/src/theme';

type Props = {
  onConfirm: () => void;
  visible: boolean;
  title?: string;
  description?: string;
};

export function SaveCompleteModal({
  onConfirm,
  visible,
  title = '변경사항이 저장되었어요',
  description = '프로필 정보가 업데이트되었어요.',
}: Props) {
  return (
    <Modal
      animationType="fade"
      onRequestClose={onConfirm}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      <View style={styles.overlay}>
        <Pressable accessibilityLabel="확인" onPress={onConfirm} style={styles.backdrop} />
        <View accessibilityViewIsModal style={[styles.card, shadow.sm]}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.description}>{description}</Text>
          <View style={styles.actions}>
            <Pressable accessibilityRole="button" onPress={onConfirm} style={[styles.button, styles.confirmButton]}>
              <Text style={styles.confirmLabel}>확인</Text>
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
  confirmButton: { backgroundColor: colors.primary },
  confirmLabel: { color: colors.surface, fontSize: 14, fontWeight: '700' },
  description: { color: colors.textSecondary, fontSize: 14, lineHeight: 21, marginTop: spacing.sm, textAlign: 'center' },
  overlay: { alignItems: 'center', backgroundColor: 'rgba(0, 0, 0, 0.48)', flex: 1, justifyContent: 'center', padding: spacing.md },
  title: { color: colors.textPrimary, fontSize: typography.body.fontSize + 1, fontWeight: '700', textAlign: 'center' },
});
