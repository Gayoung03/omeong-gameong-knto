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

type TripMemoEditModalProps = {
  initialMemo: string;
  onClose: () => void;
  onSubmit: (memo: string) => void;
};

export function TripMemoEditModal({ initialMemo, onClose, onSubmit }: TripMemoEditModalProps) {
  const [memo, setMemo] = useState(initialMemo);

  const handlePressSave = () => {
    onSubmit(memo);
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
            <Text style={styles.headerTitle}>여행 메모</Text>
            <Pressable accessibilityRole="button" hitSlop={spacing.sm} onPress={handlePressSave}>
              <Text style={styles.saveText}>저장</Text>
            </Pressable>
          </View>

          <TextInput
            autoFocus
            multiline
            onChangeText={setMemo}
            placeholder="이번 여행에서 기억해둘 점을 적어보세요"
            placeholderTextColor={colors.textTertiary}
            style={styles.input}
            textAlignVertical="top"
            value={memo}
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
  input: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    lineHeight: 22,
    minHeight: 160,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
});
