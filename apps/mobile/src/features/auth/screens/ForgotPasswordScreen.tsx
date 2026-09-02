import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { getApiErrorMessage } from '@/src/services/apiError';
import { colors } from '@/src/theme';

import { requestPasswordReset } from '../api/authApi';
import { AuthHeader } from '../components/AuthHeader';
import { IconTextField } from '../components/IconTextField';
import { PrimaryButton } from '../components/PrimaryButton';

/**
 * 비밀번호 찾기 1단계 — 이메일을 받아 인증번호를 보낸다.
 *
 * ## 안내 문구를 "메일을 보냈어요"로 쓰지 않는 이유
 *
 * 서버는 **가입 여부와 무관하게 항상 같은 응답(202)** 을 준다. 응답이 갈리면
 * 그것만으로 가입자 목록을 훑을 수 있기 때문이다. 그래서 앱도 가입돼 있는지
 * 아는 척하면 안 된다 — "가입돼 있다면 보냈다"로 적는다.
 */
export function ForgotPasswordScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string>();
  const [sending, setSending] = useState(false);

  const handleBack = () => {
    if (router.canGoBack()) router.back();
  };

  const handleSubmit = async () => {
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setError('이메일 형식을 확인해주세요.');
      return;
    }
    setError(undefined);
    // 연타로 같은 계정에 메일이 여러 통 가지 않게 잠근다. 서버에도 시간당
    // 상한이 있지만, 그건 최후의 방어선이지 UI 가 기대야 할 곳은 아니다.
    setSending(true);
    try {
      await requestPasswordReset(email);
      // 실패가 아니어도(가입 안 된 이메일이어도) 똑같이 다음 화면으로 간다.
      router.push({ pathname: '/(auth)/reset-password', params: { email } });
    } catch (caught) {
      setError(getApiErrorMessage(caught).title);
    } finally {
      setSending(false);
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
            <AuthHeader onBack={handleBack} title="비밀번호 찾기" />

            <Text style={styles.lead}>
              가입할 때 쓴 이메일을 입력하면{'\n'}인증번호를 보내드려요.
            </Text>

            <View style={styles.form}>
              <IconTextField
                autoComplete="email"
                error={error}
                icon="mail-outline"
                keyboardType="email-address"
                onChangeText={(value) => {
                  setEmail(value);
                  if (error) setError(undefined);
                }}
                onSubmitEditing={() => void handleSubmit()}
                placeholder="이메일을 입력해주세요"
                value={email}
              />
              <PrimaryButton
                label={sending ? '보내는 중...' : '인증번호 받기'}
                onPress={() => {
                  if (!sending) void handleSubmit();
                }}
              />
            </View>

            <Text style={styles.help}>
              카카오·구글로 가입했다면 비밀번호가 없어요.{'\n'}
              로그인 화면에서 해당 버튼으로 로그인해주세요.
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
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
  form: { gap: 13 },
  help: {
    color: colors.textTertiary,
    fontSize: 12,
    lineHeight: 19,
    marginTop: 24,
    textAlign: 'center',
  },
});
