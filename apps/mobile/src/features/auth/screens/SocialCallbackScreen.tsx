import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { z } from 'zod';

import { getApiErrorMessage } from '@/src/services/apiError';
import { colors } from '@/src/theme';

import {
  socialComplete,
  socialExchange,
  type LinkRequiredResponse,
  type SocialLoginResponse,
} from '../api/authApi';
import { AuthHeader } from '../components/AuthHeader';
import { IconTextField } from '../components/IconTextField';
import { PrimaryButton } from '../components/PrimaryButton';
import { completeSocialLogin } from '../services/authStorage';

type Status = 'processing' | 'link' | 'error';

// 딥링크로 들어오는 파라미터는 신뢰할 수 없으므로 zod 로 최소 검증한다.
const callbackParamsSchema = z.object({ code: z.string().min(1) });

/**
 * 카카오 로그인 복귀 화면(`/auth/callback`).
 *
 * 서버가 붙여 보낸 일회용 교환 코드(60초)를 **사용자 입력 없이 즉시** 교환한다.
 * 결과가 토큰이면 세션을 구성해 홈으로, `linkRequired` 면 비밀번호 확인 UI 를 띄운다.
 */
export function SocialCallbackScreen() {
  const router = useRouter();
  const code = callbackParamsSchema.safeParse(useLocalSearchParams()).data?.code;
  // code 유무는 첫 렌더에서 정해지므로 초기 상태로 잡는다(이펙트에서 동기 setState 금지).
  const [status, setStatus] = useState<Status>(code ? 'processing' : 'error');
  const [link, setLink] = useState<LinkRequiredResponse | null>(null);
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState<string | undefined>(
    code ? undefined : '로그인 정보를 받지 못했어요.',
  );
  const [submitting, setSubmitting] = useState(false);
  // 교환 코드는 1회성이라 중복 교환(개발 모드 이펙트 2회 실행 등)을 막는다.
  const started = useRef(false);

  const goHome = () => router.replace('/(tabs)/(home)');

  useEffect(() => {
    if (started.current || !code) return;
    started.current = true;

    // 교환 코드를 URL·네비 상태에서 **즉시** 지운다(성공/실패 무관). code 는 이미 위에서
    // 캡처했으니 요청엔 영향이 없고, 뒤로가기·브라우저 히스토리·공유로 재사용/유출되지
    // 않게 한다. 네이티브는 setParams 로 파라미터만 비워 리마운트를 피한다.
    if (Platform.OS === 'web') {
      globalThis.history?.replaceState(null, '', globalThis.location?.pathname ?? '/auth/callback');
    } else {
      router.setParams({ code: '' });
    }

    void socialExchange(code)
      .then(async (result) => {
        if ('linkRequired' in result) {
          setLink(result);
          setStatus('link');
          return;
        }
        await completeSocialLogin(result);
        // 신규 소셜 사용자의 펫·취향 온보딩은 별도 화면이 필요하다(보고 참고). 홈으로 보낸다.
        goHome();
      })
      .catch((error: unknown) => {
        setStatus('error');
        setMessage(getApiErrorMessage(error).title);
      });
  }, [code]); // eslint-disable-line react-hooks/exhaustive-deps

  const submitLink = async (action: 'link' | 'separate') => {
    if (!link || submitting) return;
    setSubmitting(true);
    setMessage(undefined);
    try {
      const result: SocialLoginResponse = await socialComplete(
        link.linkToken,
        action,
        action === 'link' ? password : undefined,
      );
      await completeSocialLogin(result);
      goHome();
    } catch (error) {
      // 비밀번호 불일치는 401. 실패해도 linkToken 은 살아 있어 다시 시도하거나
      // 별도 계정으로 이어갈 수 있다. 입력한 비밀번호는 화면에 남기지 않는다.
      setPassword('');
      setMessage(getApiErrorMessage(error).title);
    } finally {
      setSubmitting(false);
    }
  };

  if (status === 'processing') {
    return (
      <SafeAreaView style={styles.center}>
        <ActivityIndicator color={colors.primary} size="large" />
        <Text style={styles.processingText}>카카오 로그인 중이에요...</Text>
      </SafeAreaView>
    );
  }

  if (status === 'error') {
    return (
      <SafeAreaView style={styles.safeArea}>
        <AuthHeader onBack={() => router.replace('/login')} title="로그인" />
        <View style={styles.body}>
          <Text style={styles.errorText}>{message ?? '로그인에 실패했어요.'}</Text>
          <PrimaryButton label="로그인으로 돌아가기" onPress={() => router.replace('/login')} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <AuthHeader onBack={() => router.replace('/login')} title="계정 연동" />
      <View style={styles.body}>
        <Text style={styles.title}>이미 가입된 이메일이에요</Text>
        <Text style={styles.description}>
          {link?.maskedEmail} 계정과 연동하려면 비밀번호를 확인해 주세요. 원하지 않으면 별도
          계정으로 시작할 수 있어요.
        </Text>
        <IconTextField
          icon="lock-closed-outline"
          onChangeText={setPassword}
          password
          placeholder="비밀번호"
          value={password}
        />
        {message && <Text style={styles.errorText}>{message}</Text>}
        <PrimaryButton
          icon="link"
          label={submitting ? '처리 중...' : '비밀번호 확인 후 연동'}
          onPress={() => void submitLink('link')}
        />
        <Pressable onPress={() => void submitLink('separate')} style={styles.separateButton}>
          <Text style={styles.separateLabel}>별도 계정으로 시작하기</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: colors.surface, flex: 1 },
  center: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    flex: 1,
    gap: 16,
    justifyContent: 'center',
  },
  processingText: { color: colors.textSecondary, fontSize: 14 },
  body: {
    alignSelf: 'center',
    gap: 14,
    maxWidth: 520,
    paddingHorizontal: 24,
    paddingTop: 8,
    width: '100%',
  },
  title: { color: colors.textPrimary, fontSize: 22, fontWeight: '900', letterSpacing: -0.6 },
  description: { color: colors.textSecondary, fontSize: 14, lineHeight: 21 },
  errorText: { color: colors.warning, fontSize: 13 },
  separateButton: { alignItems: 'center', minHeight: 48, justifyContent: 'center' },
  separateLabel: { color: colors.primary, fontSize: 14, fontWeight: '700' },
});
