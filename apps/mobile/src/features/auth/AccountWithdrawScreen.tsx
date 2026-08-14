import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, radius, spacing, typography } from '@/src/theme';

import { WithdrawConfirmModal } from './components/WithdrawConfirmModal';
import { WithdrawDeletionCard } from './components/WithdrawDeletionCard';
import { useWithdrawAccount } from './hooks/useWithdrawAccount';

export function AccountWithdrawScreen() {
  const router = useRouter();
  const { withdraw, isPending, errorMessage } = useWithdrawAccount();
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [isConfirmModalVisible, setConfirmModalVisible] = useState(false);

  const isWithdrawDisabled = !isConfirmed || isPending;

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="회원 탈퇴" />
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.notice}>
          <View style={styles.noticeIcon}>
            <Ionicons color={colors.error} name="alert" size={28} />
          </View>
          <Text style={styles.noticeTitle}>정말 탈퇴하시겠어요?</Text>
          <Text style={styles.noticeDescription}>
            회원 탈퇴 시 아래 정보가 삭제되며,{'\n'}삭제된 정보는 복구할 수 없습니다.
          </Text>
          <Text style={styles.noticeHighlight}>
            또한 탈퇴가 완료되면 동일한 이메일로{'\n'}다시 가입할 수 없습니다.
          </Text>
        </View>

        <WithdrawDeletionCard />

        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked: isConfirmed, disabled: isPending }}
          disabled={isPending}
          onPress={() => setIsConfirmed((current) => !current)}
          style={styles.checkRow}
        >
          <View style={[styles.checkbox, isConfirmed && styles.checkboxChecked]}>
            {isConfirmed ? <Ionicons color={colors.surface} name="checkmark" size={14} /> : null}
          </View>
          <Text style={styles.checkLabel}>데이터 삭제 및 재가입 제한 내용을 확인했어요.</Text>
        </Pressable>

        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}

        <View style={styles.actions}>
          <Pressable
            accessibilityRole="button"
            disabled={isPending}
            onPress={() => router.back()}
            style={[styles.button, styles.cancelButton]}
          >
            <Text style={styles.cancelLabel}>취소</Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ disabled: isWithdrawDisabled }}
            disabled={isWithdrawDisabled}
            onPress={() => setConfirmModalVisible(true)}
            style={[
              styles.button,
              styles.withdrawButton,
              isWithdrawDisabled && styles.withdrawButtonDisabled,
            ]}
          >
            {isPending ? (
              <ActivityIndicator color={colors.surface} size="small" />
            ) : (
              <Text style={[styles.withdrawLabel, isWithdrawDisabled && styles.withdrawLabelDisabled]}>
                탈퇴하기
              </Text>
            )}
          </Pressable>
        </View>
      </ScrollView>

      <WithdrawConfirmModal
        isPending={isPending}
        onCancel={() => setConfirmModalVisible(false)}
        onConfirm={() => {
          void withdraw().finally(() => setConfirmModalVisible(false));
        }}
        visible={isConfirmModalVisible}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingTop: spacing.sm,
  },
  button: {
    alignItems: 'center',
    borderRadius: radius.md,
    flex: 1,
    justifyContent: 'center',
    minHeight: 52,
    paddingHorizontal: spacing.sm,
  },
  cancelButton: {
    backgroundColor: colors.neutralGray,
  },
  cancelLabel: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize - 1,
    fontWeight: '700',
  },
  checkLabel: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.body.fontSize - 2,
    lineHeight: 22,
  },
  checkRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    paddingVertical: spacing.sm,
  },
  checkbox: {
    alignItems: 'center',
    borderColor: colors.border,
    borderRadius: radius.sm - 2,
    borderWidth: 1,
    height: 22,
    justifyContent: 'center',
    width: 22,
  },
  checkboxChecked: {
    backgroundColor: colors.error,
    borderColor: colors.error,
  },
  content: {
    gap: spacing.lg,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  errorText: {
    color: colors.error,
    fontSize: typography.body.fontSize - 3,
    textAlign: 'center',
  },
  notice: {
    alignItems: 'center',
    gap: spacing.sm,
  },
  noticeDescription: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    lineHeight: 22,
    textAlign: 'center',
  },
  noticeHighlight: {
    color: colors.error,
    fontSize: typography.body.fontSize - 2,
    fontWeight: '600',
    lineHeight: 22,
    textAlign: 'center',
  },
  noticeIcon: {
    alignItems: 'center',
    backgroundColor: colors.errorBg,
    borderRadius: 9999,
    height: 64,
    justifyContent: 'center',
    marginBottom: spacing.xs,
    width: 64,
  },
  noticeTitle: {
    color: colors.textPrimary,
    fontSize: typography.title.fontSize - 2,
    fontWeight: '700',
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  withdrawButton: {
    backgroundColor: colors.error,
  },
  withdrawButtonDisabled: {
    backgroundColor: colors.errorBg,
  },
  withdrawLabel: {
    color: colors.surface,
    fontSize: typography.body.fontSize - 1,
    fontWeight: '700',
  },
  withdrawLabelDisabled: {
    color: colors.error,
    opacity: 0.5,
  },
});
