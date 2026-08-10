import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, overlayColors, radius, shadow, spacing, typography } from '@/src/theme';

type Props = {
  petName: string;
  visible: boolean;
  isDeleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function PetDeleteConfirmModal({
  petName,
  visible,
  isDeleting,
  onCancel,
  onConfirm,
}: Props) {
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
          <Text style={styles.title}>{petName}의 프로필을 지울까요?</Text>
          <Text style={styles.description}>
            등록된 프로필 정보가 삭제되며,{'\n'}기존 여행 기록에는 영향을 주지 않아요.
          </Text>
          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              disabled={isDeleting}
              onPress={onCancel}
              style={[styles.button, styles.cancelButton]}
            >
              <Text style={styles.cancelLabel}>취소</Text>
            </Pressable>
            {/* 삭제 요청 중에는 중복 클릭을 막는다. */}
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: isDeleting }}
              disabled={isDeleting}
              onPress={onConfirm}
              style={[styles.button, styles.deleteButton, isDeleting && styles.deleteButtonBusy]}
            >
              <Text style={styles.deleteLabel}>{isDeleting ? '지우는 중...' : '지우기'}</Text>
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
  deleteButton: { backgroundColor: colors.error },
  deleteButtonBusy: { opacity: 0.6 },
  deleteLabel: { color: colors.surface, fontSize: 14, fontWeight: '700' },
  description: { color: colors.textSecondary, fontSize: 14, lineHeight: 21, marginTop: spacing.sm, textAlign: 'center' },
  overlay: { alignItems: 'center', backgroundColor: overlayColors.dim, flex: 1, justifyContent: 'center', padding: spacing.md },
  title: { color: colors.textPrimary, fontSize: typography.body.fontSize + 1, fontWeight: '700', textAlign: 'center' },
});
