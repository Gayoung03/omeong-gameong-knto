import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, radius, spacing, typography } from '@/src/theme';

import { type AuthProvider } from './api/authApi';
import { IconTextField } from './components/IconTextField';
import { WithdrawConfirmModal } from './components/WithdrawConfirmModal';
import { WithdrawDeletionCard } from './components/WithdrawDeletionCard';
import { useWithdrawAccount } from './hooks/useWithdrawAccount';
import { getAuthSession } from './services/authStorage';

export function AccountWithdrawScreen() {
  const router = useRouter();
  const { withdraw, isPending, errorMessage } = useWithdrawAccount();
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [isConfirmModalVisible, setConfirmModalVisible] = useState(false);
  const [password, setPassword] = useState('');
  const [authProvider, setAuthProvider] = useState<AuthProvider>();

  useEffect(() => {
    // 탈퇴가 비밀번호(local)냐 제공처 재인증(소셜)이냐를 세션의 가입 수단으로 가른다.
    void getAuthSession().then((session) => setAuthProvider(session?.authProvider));
  }, []);

  // 소셜 계정 탈퇴는 제공처 재인증 흐름(카카오 재로그인)이 아직 없어 준비 중이다.
  // authProvider 가 아직 로딩 안 됐으면(undefined) local 로 본다(대부분 local).
  const isSocial = authProvider !== undefined && authProvider !== 'local';
  const isWithdrawDisabled =
    !isConfirmed || isPending || isSocial || password.trim().length === 0;

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

        {isSocial ? (
          <View style={styles.socialNotice}>
            <Ionicons color={colors.textSecondary} name="information-circle-outline" size={20} />
            <Text style={styles.socialNoticeText}>
              소셜 계정 탈퇴는 준비 중이에요. 곧 지원할 예정이에요.
            </Text>
          </View>
        ) : (
          <IconTextField
            icon="lock-closed-outline"
            onChangeText={setPassword}
            password
            placeholder="비밀번호 확인"
            value={password}
          />
        )}

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
          void withdraw(password).finally(() => setConfirmModalVisible(false));
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
  socialNotice: {
    alignItems: 'center',
    backgroundColor: colors.neutralGray,
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
  },
  socialNoticeText: {
    color: colors.textSecondary,
    flex: 1,
    fontSize: typography.body.fontSize - 2,
    lineHeight: 20,
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
