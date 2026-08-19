import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { brandColors, colors } from '@/src/theme';

import { AuthBrand } from '../components/AuthBrand';
import { AuthHeader } from '../components/AuthHeader';
import { IconTextField } from '../components/IconTextField';
import { PrimaryButton } from '../components/PrimaryButton';
import { getAuthSession, signIn } from '../services/authStorage';

/**
 * 각 사의 브랜드 가이드라인에 규정된 색이라 theme 토큰으로 치환하지 않는다.
 * 값은 `theme/colors.ts` 의 `brandColors` 에 모아두었다.
 */
const socialProviders = [
  { label: '네이버', shortLabel: 'N', ...brandColors.naver },
  { label: '카카오', shortLabel: '●', ...brandColors.kakao },
  { label: '구글', shortLabel: 'G', ...brandColors.google },
];

export function LoginScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});

  useEffect(() => {
    void getAuthSession().then((session) => {
      if (session) router.replace('/(tabs)/(home)');
    });
  }, [router]);

  const handleBack = () => {
    if (router.canGoBack()) router.back();
  };

  const handleLogin = async () => {
    const nextErrors: typeof errors = {};
    if (!/^\S+@\S+\.\S+$/.test(email)) nextErrors.email = '이메일 형식을 확인해주세요.';
    if (password.length < 8) nextErrors.password = '비밀번호를 8자 이상 입력해주세요.';
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    await signIn(email);
    router.replace('/(tabs)/(home)');
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
            <AuthHeader onBack={handleBack} />
            <AuthBrand />

            <View style={styles.form}>
              <IconTextField
                autoComplete="email"
                error={errors.email}
                icon="mail-outline"
                keyboardType="email-address"
                onChangeText={(value) => {
                  setEmail(value);
                  if (errors.email) setErrors((current) => ({ ...current, email: undefined }));
                }}
                placeholder="이메일을 입력해주세요"
                value={email}
              />
              <IconTextField
                autoComplete="current-password"
                error={errors.password}
                icon="lock-closed-outline"
                onChangeText={(value) => {
                  setPassword(value);
                  if (errors.password) {
                    setErrors((current) => ({ ...current, password: undefined }));
                  }
                }}
                onSubmitEditing={() => void handleLogin()}
                password
                placeholder="비밀번호를 입력해주세요"
                value={password}
              />

              <View style={styles.formOptions}>
                <Pressable
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: remember }}
                  onPress={() => setRemember((value) => !value)}
                  style={styles.rememberRow}
                >
                  <View style={[styles.checkbox, remember && styles.checkboxChecked]}>
                    {remember && <Ionicons color={colors.surface} name="checkmark" size={13} />}
                  </View>
                  <Text style={styles.optionText}>로그인 상태 유지</Text>
                </Pressable>
                <Pressable onPress={() => Alert.alert('준비 중', '비밀번호 찾기는 추후 연결됩니다.')}>
                  <Text style={styles.optionText}>비밀번호 찾기</Text>
                </Pressable>
              </View>

              <PrimaryButton label="로그인" onPress={() => void handleLogin()} />
            </View>

            <View style={styles.dividerRow}>
              <View style={styles.divider} />
              <Text style={styles.dividerText}>또는 다른 방법으로 로그인</Text>
              <View style={styles.divider} />
            </View>

            <View style={styles.socialRow}>
              {socialProviders.map((provider) => (
                <Pressable
                  accessibilityLabel={`${provider.label} 로그인`}
                  key={provider.label}
                  onPress={() => Alert.alert('추후 연동', `${provider.label} 로그인을 연결할 예정입니다.`)}
                  style={({ pressed }) => [
                    styles.socialButton,
                    { backgroundColor: provider.background },
                    pressed && styles.pressed,
                  ]}
                >
                  <Text style={[styles.socialLabel, { color: provider.text }]}>
                    {provider.shortLabel}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Pressable onPress={() => router.push('/signup')} style={styles.signupPrompt}>
              <Text style={styles.signupPromptText}>계정이 없으신가요?</Text>
              <Text style={styles.signupLink}>회원가입</Text>
              <Ionicons color={colors.primary} name="arrow-forward" size={17} />
            </Pressable>
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
  form: { gap: 13, marginTop: 4 },
  formOptions: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  rememberRow: { alignItems: 'center', flexDirection: 'row', gap: 7 },
  checkbox: {
    alignItems: 'center',
    borderColor: colors.divider,
    borderRadius: 4,
    borderWidth: 1,
    height: 18,
    justifyContent: 'center',
    width: 18,
  },
  checkboxChecked: { backgroundColor: colors.primary, borderColor: colors.primary },
  optionText: { color: colors.textStrong, fontSize: 13 },
  dividerRow: { alignItems: 'center', flexDirection: 'row', gap: 12, marginTop: 26 },
  divider: { backgroundColor: colors.border, flex: 1, height: 1 },
  dividerText: { color: colors.iconGray, fontSize: 12 },
  socialRow: { flexDirection: 'row', gap: 20, justifyContent: 'center', marginTop: 18 },
  socialButton: {
    alignItems: 'center',
    borderColor: colors.divider,
    borderRadius: 25,
    borderWidth: 1,
    height: 50,
    justifyContent: 'center',
    width: 50,
  },
  socialLabel: { fontSize: 22, fontWeight: '900' },
  pressed: { opacity: 0.7 },
  signupPrompt: {
    alignItems: 'center',
    borderColor: colors.basaltSoft,
    borderRadius: 14,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 5,
    justifyContent: 'center',
    marginTop: 24,
    minHeight: 58,
  },
  signupPromptText: { color: colors.textStrong, fontSize: 14 },
  signupLink: { color: colors.primary, fontSize: 14, fontWeight: '800' },
});

