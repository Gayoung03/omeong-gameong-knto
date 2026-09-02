import { isAxiosError } from 'axios';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { getApiErrorMessage } from '@/src/services/apiError';
import { colors } from '@/src/theme';

import { confirmPasswordReset, requestPasswordReset, verifyPasswordResetCode } from '../api/authApi';
import { AuthHeader } from '../components/AuthHeader';
import { IconTextField } from '../components/IconTextField';
import { PrimaryButton } from '../components/PrimaryButton';

/** 서버의 `PASSWORD_MIN_LENGTH` 와 같은 값. 어긋나면 앱이 통과시킨 값이 422 로 돌아온다. */
const PASSWORD_MIN_LENGTH = 8;

/**
 * 비밀번호 찾기 2단계 — 인증번호 확인 → 새 비밀번호 설정.
 *
 * ## 왜 한 화면에 몰지 않는가
 *
 * 인증번호와 새 비밀번호를 같이 받으면, 코드가 틀렸다는 것을 **비밀번호까지 다
 * 입력한 뒤에야** 알게 된다. 그래서 코드를 먼저 서버에 확인시키고
 * (`/auth/password-reset/verify` — 코드를 소모하지 않는다) 통과한 다음에
 * 비밀번호를 받는다.
 *
 * 확인을 통과했어도 마지막 요청에서 서버가 코드를 **다시** 검사한다. 그 사이
 * 코드가 만료(10분)될 수 있어서다. 그때는 인증번호 단계로 되돌린다 — 새
 * 비밀번호 화면에 남겨두면 사용자가 같은 버튼만 계속 누른다.
 *
 * 성공해도 토큰이 오지 않는다(서버는 204). 바뀐 비밀번호로 로그인 화면을 한 번
 * 거치게 하는 것이 명세다 — 재설정 시점에 기존 토큰이 전부 무효가 되므로,
 * 여기서 로그인 상태를 만들면 경계가 헷갈린다.
 */
export function ResetPasswordScreen() {
  const router = useRouter();
  const { email } = useLocalSearchParams<{ email: string }>();
  const [step, setStep] = useState<'code' | 'password'>('code');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [errors, setErrors] = useState<{
    code?: string;
    password?: string;
    passwordConfirm?: string;
  }>({});
  const [notice, setNotice] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

  const clearError = (field: keyof typeof errors) => {
    if (errors[field]) setErrors((current) => ({ ...current, [field]: undefined }));
  };

  /** 인증번호 단계로 되돌린다. 새 비밀번호는 지운다 — 코드가 바뀌면 다시 받아야 한다. */
  const backToCodeStep = (message?: string) => {
    setStep('code');
    setPassword('');
    setPasswordConfirm('');
    setNotice(message);
  };

  const handleBack = () => {
    // 비밀번호 단계에서는 화면을 나가는 대신 인증번호 단계로 돌아간다.
    if (step === 'password') {
      backToCodeStep();
      return;
    }
    if (router.canGoBack()) router.back();
  };

  const handleVerify = async () => {
    if (!/^\d{6}$/.test(code)) {
      setErrors({ code: '인증번호 6자리를 입력해주세요.' });
      return;
    }

    setNotice(undefined);
    setSubmitting(true);
    try {
      await verifyPasswordResetCode(email, code);
      setErrors({});
      setStep('password');
    } catch (caught) {
      setNotice(resolveErrorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    const nextErrors: typeof errors = {};
    if (password.length < PASSWORD_MIN_LENGTH) {
      nextErrors.password = `비밀번호를 ${PASSWORD_MIN_LENGTH}자 이상 입력해주세요.`;
    }
    if (passwordConfirm !== password) {
      nextErrors.passwordConfirm = '비밀번호가 서로 달라요.';
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setNotice(undefined);
    setSubmitting(true);
    try {
      await confirmPasswordReset(email, code, password);
      // 재설정을 마치면 기존 세션이 전부 끊긴 상태다. 뒤로가기로 이 화면에
      // 돌아오지 않도록 replace 로 로그인 화면을 덮는다.
      router.replace('/(auth)/login');
    } catch (caught) {
      // 확인까지 통과한 코드가 여기서 막혔다면 그 사이 만료·소진된 것이다.
      // 인증번호 단계로 되돌려야 사용자가 다음에 뭘 할지 알 수 있다.
      backToCodeStep(resolveErrorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setNotice(undefined);
    try {
      await requestPasswordReset(email);
      setCode('');
      setNotice('인증번호를 다시 보냈어요. 이전 번호는 사용할 수 없어요.');
    } catch (caught) {
      setNotice(getApiErrorMessage(caught).title);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.screen}>
            <AuthHeader onBack={handleBack} title="비밀번호 재설정" />

            <Text style={styles.lead}>
              <Text style={styles.email}>{email}</Text>
              {'\n'}
              {step === 'code'
                ? '가입돼 있다면 인증번호가 담긴 메일이 갔어요.'
                : '인증번호를 확인했어요. 새 비밀번호를 정해주세요.'}
            </Text>

            {step === 'code' ? (
              <View style={styles.form}>
                <IconTextField
                  error={errors.code}
                  icon="keypad-outline"
                  keyboardType="number-pad"
                  maxLength={6}
                  onChangeText={(value) => {
                    // 숫자만 남긴다 — 메일에서 복사하면 공백이 딸려오는 일이 잦다.
                    setCode(value.replace(/\D/g, ''));
                    clearError('code');
                  }}
                  onSubmitEditing={() => void handleVerify()}
                  placeholder="인증번호 6자리"
                  value={code}
                />

                {notice && <Text style={styles.noticeText}>{notice}</Text>}

                <PrimaryButton
                  label={submitting ? '확인 중...' : '다음'}
                  onPress={() => {
                    if (!submitting) void handleVerify();
                  }}
                />
              </View>
            ) : (
              <View style={styles.form}>
                <IconTextField
                  autoComplete="new-password"
                  error={errors.password}
                  icon="lock-closed-outline"
                  onChangeText={(value) => {
                    setPassword(value);
                    clearError('password');
                    clearError('passwordConfirm');
                  }}
                  password
                  placeholder={`새 비밀번호 (${PASSWORD_MIN_LENGTH}자 이상)`}
                  value={password}
                />
                <IconTextField
                  autoComplete="new-password"
                  error={errors.passwordConfirm}
                  icon="lock-closed-outline"
                  onChangeText={(value) => {
                    setPasswordConfirm(value);
                    clearError('passwordConfirm');
                  }}
                  onSubmitEditing={() => void handleSubmit()}
                  password
                  placeholder="새 비밀번호 확인"
                  value={passwordConfirm}
                />

                {notice && <Text style={styles.noticeText}>{notice}</Text>}

                <PrimaryButton
                  label={submitting ? '변경 중...' : '비밀번호 변경'}
                  onPress={() => {
                    if (!submitting) void handleSubmit();
                  }}
                />
              </View>
            )}

            {step === 'code' && (
              <Pressable onPress={() => void handleResend()} style={styles.resend}>
                <Text style={styles.resendText}>메일이 오지 않았나요? 다시 받기</Text>
              </Pressable>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

/**
 * 서버는 없음·만료·사용됨·불일치를 구분하지 않고 400 으로 준다(유효한 코드를
 * 찾는 힌트가 되지 않도록). 429 만 구분해서 알려준다 — 안 알려주면 사용자가
 * 이미 죽은 코드를 계속 입력한다.
 */
function resolveErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    if (error.response?.status === 429) {
      return '입력을 너무 여러 번 시도했어요. 인증번호를 다시 받아주세요.';
    }
    if (error.response?.status === 400) {
      return '인증번호가 올바르지 않거나 만료됐어요.';
    }
  }
  return getApiErrorMessage(error).title;
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  safeArea: { backgroundColor: colors.surface, flex: 1 },
  scrollContent: { flexGrow: 1 },
  screen: {
    alignSelf: 'center',
    flex: 1,
    maxWidth: 520,
    paddingBottom: 28,
    paddingHorizontal: 24,
    width: '100%',
  },
  lead: {
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 22,
    marginBottom: 22,
    marginTop: 8,
  },
  email: { color: colors.textStrong, fontWeight: '700' },
  form: { gap: 13 },
  noticeText: {
    color: colors.textSecondary,
    fontSize: 13,
    paddingVertical: 2,
    textAlign: 'center',
  },
  resend: { alignItems: 'center', marginTop: 22 },
  resendText: { color: colors.textStrong, fontSize: 13, textDecorationLine: 'underline' },
});
