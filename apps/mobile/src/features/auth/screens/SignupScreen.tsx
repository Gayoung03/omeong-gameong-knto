import Ionicons from '@expo/vector-icons/Ionicons';
import { isAxiosError } from 'axios';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { getApiErrorMessage } from '@/src/services/apiError';
import { colors } from '@/src/theme';

import { AgreementSection, hasAllRequiredAgreements } from '../components/AgreementSection';
import { AuthHeader } from '../components/AuthHeader';
import { ChoiceChip } from '../components/ChoiceChip';
import { IconTextField } from '../components/IconTextField';
import { PrimaryButton } from '../components/PrimaryButton';
import { SignupProgress } from '../components/SignupProgress';
import {
  durationOptions,
  petSizeOptions,
  petTypeOptions,
  transportOptions,
  vibeOptions,
} from '../constants/signupOptions';
import { completeSignup } from '../services/authStorage';
import type { SignupData } from '../types/auth';

const initialData: SignupData = {
  agreements: { age14: false, terms: false, privacy: false, marketing: false },
  account: { email: '', password: '', passwordConfirm: '', nickname: '' },
  pet: { name: '', type: null, typeDetail: '', size: null },
  travel: {
    duration: null,
    transport: null,
    departure: '',
    vibes: [],
    companions: 1,
  },
};

type AccountErrors = Partial<Record<keyof SignupData['account'], string>>;

export function SignupScreen() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [data, setData] = useState<SignupData>(initialData);
  const [accountErrors, setAccountErrors] = useState<AccountErrors>({});
  const [agreementError, setAgreementError] = useState<string>();
  const [petError, setPetError] = useState<string>();
  const [submitError, setSubmitError] = useState<string>();
  const [submitting, setSubmitting] = useState(false);

  const updateAccount = (key: keyof SignupData['account'], value: string) => {
    setData((current) => ({
      ...current,
      account: { ...current.account, [key]: value },
    }));
    if (accountErrors[key]) {
      setAccountErrors((current) => ({ ...current, [key]: undefined }));
    }
  };

  const validateAccount = () => {
    const errors: AccountErrors = {};
    if (!/^\S+@\S+\.\S+$/.test(data.account.email)) {
      errors.email = '사용할 이메일 주소를 정확히 입력해주세요.';
    }
    if (data.account.password.length < 8) {
      errors.password = '영문, 숫자를 포함해 8자 이상 입력해주세요.';
    }
    if (data.account.passwordConfirm !== data.account.password) {
      errors.passwordConfirm = '비밀번호가 일치하지 않습니다.';
    }
    if (data.account.nickname.trim().length < 2) {
      errors.nickname = '닉네임을 2자 이상 입력해주세요.';
    }
    setAccountErrors(errors);

    const agreementsMissing = !hasAllRequiredAgreements(data.agreements);
    setAgreementError(agreementsMissing ? '필수 항목에 모두 동의해주세요.' : undefined);

    return Object.keys(errors).length === 0 && !agreementsMissing;
  };

  /**
   * 펫 단계 검증. 펫 정보를 하나라도 채웠으면 완전한 펫(종류·이름·기타상세)을 요구하고,
   * 전부 비었으면 통과시켜 펫을 보내지 않는다(기존 "선택" 동작). 백엔드 pet 규칙과
   * 맞춘다 — name 필수(1~50자), species=other 면 speciesDetail 필수.
   */
  const validatePet = () => {
    const name = data.pet.name.trim();
    const hasAnyInfo =
      data.pet.type !== null ||
      data.pet.size !== null ||
      name.length > 0 ||
      data.pet.typeDetail.trim().length > 0;

    if (!hasAnyInfo) {
      setPetError(undefined);
      return true;
    }
    if (data.pet.type === null) {
      setPetError('반려동물 종류를 선택해주세요.');
      return false;
    }
    if (name.length === 0 || name.length > 50) {
      setPetError('반려동물 이름을 1~50자로 입력해주세요.');
      return false;
    }
    if (data.pet.type === 'other' && data.pet.typeDetail.trim().length === 0) {
      setPetError('기타 종의 종류를 입력해주세요.');
      return false;
    }
    setPetError(undefined);
    return true;
  };

  const goNext = () => {
    setSubmitError(undefined);
    if (step === 1 && !validateAccount()) return;
    if (step === 2 && !validatePet()) return;
    setStep((current) => Math.min(current + 1, 3));
  };

  const handleBack = () => {
    if (step > 1) {
      setStep((current) => current - 1);
      return;
    }
    // 새로고침이나 딥링크로 바로 들어오면 돌아갈 화면이 없어 back 이 실패한다.
    if (router.canGoBack()) {
      router.back();
      return;
    }
    router.replace('/login');
  };

  const skipCurrentStep = () => {
    if (step === 2) {
      setPetError(undefined);
      setData((current) => ({
        ...current,
        pet: { name: '', type: null, typeDetail: '', size: null },
      }));
      setStep(3);
      return;
    }
    if (step === 3) void finishSignup();
  };

  const finishSignup = async () => {
    if (submitting) return;
    setSubmitting(true);
    setSubmitError(undefined);
    try {
      await completeSignup(data);
      router.replace('/(tabs)/(home)');
    } catch (error) {
      handleSignupError(error);
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * 가입 제출 실패를 화면에 남긴다(무반응 방지).
   *
   * Alert 은 웹에서 안 떠 눌러도 반응이 없어 보이므로, LoginScreen 처럼 화면 내
   * 문구로 알린다. 계정 원인(409·422)은 1단계로 돌려보내 이메일 필드/상단 문구로,
   * 그 밖(네트워크·서버)은 3단계 상단 문구로.
   */
  const handleSignupError = (error: unknown) => {
    const status = isAxiosError(error) ? error.response?.status : undefined;

    if (status === 409) {
      // 이미 가입된 이메일(탈퇴 계정 포함, auth.md). 이메일 단계로 되돌린다.
      setAccountErrors((current) => ({
        ...current,
        email: '이미 가입된 이메일이에요. 다른 이메일을 사용해주세요.',
      }));
      setStep(1);
      return;
    }
    if (status === 422) {
      // 입력 규칙 위반(비밀번호 규칙 등). 계정 단계로 돌려 다시 확인하게 한다.
      setStep(1);
      setSubmitError(getApiErrorMessage(error).description);
      return;
    }
    setSubmitError(getApiErrorMessage(error).title);
  };

  const toggleVibe = (value: string) => {
    setData((current) => ({
      ...current,
      travel: {
        ...current.travel,
        vibes: current.travel.vibes.includes(value)
          ? current.travel.vibes.filter((item) => item !== value)
          : [...current.travel.vibes, value],
      },
    }));
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
            <AuthHeader
              actionLabel={step > 1 ? '건너뛰기' : undefined}
              onAction={step > 1 ? skipCurrentStep : undefined}
              onBack={handleBack}
              title="회원가입"
            />
            <SignupProgress currentStep={step} />

            {submitError && <Text style={styles.submitError}>{submitError}</Text>}

            {step === 1 && (
              <View>
                <StepIntro
                  description="오멍가멍과 함께 특별한 제주 여행을 시작해요."
                  title="계정 정보를 입력해주세요"
                />
                <View style={styles.fieldList}>
                  <IconTextField
                    autoComplete="email"
                    error={accountErrors.email}
                    icon="mail-outline"
                    keyboardType="email-address"
                    onChangeText={(value) => updateAccount('email', value)}
                    placeholder="이메일 주소"
                    value={data.account.email}
                  />
                  <IconTextField
                    autoComplete="new-password"
                    error={accountErrors.password}
                    icon="lock-closed-outline"
                    onChangeText={(value) => updateAccount('password', value)}
                    password
                    placeholder="비밀번호 (8자 이상)"
                    value={data.account.password}
                  />
                  <IconTextField
                    autoComplete="new-password"
                    error={accountErrors.passwordConfirm}
                    icon="lock-closed-outline"
                    onChangeText={(value) => updateAccount('passwordConfirm', value)}
                    password
                    placeholder="비밀번호 확인"
                    value={data.account.passwordConfirm}
                  />
                  <IconTextField
                    autoCapitalize="words"
                    error={accountErrors.nickname}
                    icon="person-outline"
                    onChangeText={(value) => updateAccount('nickname', value)}
                    placeholder="닉네임"
                    value={data.account.nickname}
                  />
                </View>
                <AgreementSection
                  error={agreementError}
                  onChange={(agreements) => {
                    setData((current) => ({ ...current, agreements }));
                    if (agreementError) setAgreementError(undefined);
                  }}
                  value={data.agreements}
                />
                <PrimaryButton icon="chevron-forward" label="다음" onPress={goNext} />
                <InfoCard />
              </View>
            )}

            {step === 2 && (
              <View>
                <StepIntro
                  description="함께 여행할 반려동물의 특징을 알려주세요. 나중에 마이페이지에서 바꿀 수 있어요."
                  title="반려동물 정보를 알려주세요"
                />

                <Section title="반려동물 종류">
                  <View style={styles.petTypeGrid}>
                    {petTypeOptions.map((option) => {
                      const selected = data.pet.type === option.value;
                      return (
                        <Pressable
                          accessibilityState={{ selected }}
                          key={option.value}
                          onPress={() =>
                            setData((current) => ({
                              ...current,
                              pet: {
                                ...current.pet,
                                type: option.value,
                                typeDetail:
                                  option.value === 'other' ? current.pet.typeDetail : '',
                              },
                            }))
                          }
                          style={({ pressed }) => [
                            styles.petTypeCard,
                            selected && styles.petTypeCardSelected,
                            pressed && styles.pressed,
                          ]}
                        >
                          <Text style={styles.petEmoji}>{option.icon}</Text>
                          <Text style={[styles.petLabel, selected && styles.petLabelSelected]}>
                            {option.label}
                          </Text>
                        </Pressable>
                      );
                    })}
                  </View>
                  {data.pet.type === 'other' && (
                    <TextInput
                      maxLength={20}
                      onChangeText={(value) =>
                        setData((current) => ({
                          ...current,
                          pet: { ...current.pet, typeDetail: value.replace(/\n/g, '') },
                        }))
                      }
                      placeholder="종 이름을 입력해주세요"
                      placeholderTextColor={colors.textTertiary}
                      style={styles.speciesDetailInput}
                      value={data.pet.typeDetail}
                    />
                  )}
                </Section>

                <Section title="반려동물 이름">
                  <IconTextField
                    error={petError}
                    icon="paw-outline"
                    maxLength={50}
                    onChangeText={(value) => {
                      setData((current) => ({
                        ...current,
                        pet: { ...current.pet, name: value },
                      }));
                      if (petError) setPetError(undefined);
                    }}
                    placeholder="반려동물 이름 (입력 시 필수)"
                    value={data.pet.name}
                  />
                </Section>

                <Section title="반려동물 크기">
                  <View style={styles.row}>
                    {petSizeOptions.map((option) => (
                      <ChoiceChip
                        grow
                        key={option.value}
                        label={option.label}
                        onPress={() =>
                          setData((current) => ({
                            ...current,
                            pet: { ...current.pet, size: option.value },
                          }))
                        }
                        selected={data.pet.size === option.value}
                      />
                    ))}
                  </View>
                </Section>

                <View style={styles.bottomAction}>
                  <PrimaryButton icon="chevron-forward" label="여행 스타일 입력하기" onPress={goNext} />
                  <Text style={styles.optionalHint}>선택하지 않은 정보는 비워진 상태로 저장됩니다.</Text>
                </View>
              </View>
            )}

            {step === 3 && (
              <View>
                <StepIntro
                  description="취향을 저장해두면 나중에 더 잘 맞는 제주 여행지를 추천할 수 있어요."
                  title="여행 스타일을 알려주세요"
                />

                <Section optional title="선호 여행일수">
                  <View style={styles.wrapRow}>
                    {durationOptions.map((option) => (
                      <ChoiceChip
                        key={option}
                        label={option}
                        onPress={() =>
                          setData((current) => ({
                            ...current,
                            travel: { ...current.travel, duration: option },
                          }))
                        }
                        selected={data.travel.duration === option}
                      />
                    ))}
                  </View>
                </Section>

                <Section optional title="선호 이동수단">
                  <View style={styles.wrapRow}>
                    {transportOptions.map((option) => (
                      <ChoiceChip
                        icon={option.icon}
                        key={option.value}
                        label={option.value}
                        onPress={() =>
                          setData((current) => ({
                            ...current,
                            travel: { ...current.travel, transport: option.value },
                          }))
                        }
                        selected={data.travel.transport === option.value}
                      />
                    ))}
                  </View>
                </Section>

                <Section optional title="출발 지역">
                  <View style={styles.departureField}>
                    <Ionicons color={colors.textSecondary} name="location-outline" size={21} />
                    <TextInput
                      onChangeText={(departure) =>
                        setData((current) => ({
                          ...current,
                          travel: { ...current.travel, departure },
                        }))
                      }
                      placeholder="예: 서울, 부산, 대구"
                      placeholderTextColor={colors.textTertiary}
                      style={styles.departureInput}
                      value={data.travel.departure}
                    />
                  </View>
                </Section>

                <Section optional title="선호 분위기 (복수 선택 가능)">
                  <View style={styles.wrapRow}>
                    {vibeOptions.map((option) => (
                      <ChoiceChip
                        icon={option.icon}
                        key={option.value}
                        label={option.value}
                        onPress={() => toggleVibe(option.value)}
                        selected={data.travel.vibes.includes(option.value)}
                      />
                    ))}
                  </View>
                </Section>

                <Section title="함께 여행하는 인원">
                  <View style={styles.counterRow}>
                    <Text style={styles.counterDescription}>본인을 포함한 동반 인원</Text>
                    <View style={styles.counter}>
                      <Pressable
                        accessibilityLabel="인원 줄이기"
                        disabled={data.travel.companions <= 1}
                        onPress={() =>
                          setData((current) => ({
                            ...current,
                            travel: {
                              ...current.travel,
                              companions: Math.max(1, current.travel.companions - 1),
                            },
                          }))
                        }
                        style={styles.counterButton}
                      >
                        <Ionicons
                          color={data.travel.companions <= 1 ? colors.textTertiary : colors.textPrimary}
                          name="remove"
                          size={20}
                        />
                      </Pressable>
                      <Text style={styles.counterValue}>{data.travel.companions}명</Text>
                      <Pressable
                        accessibilityLabel="인원 늘리기"
                        onPress={() =>
                          setData((current) => ({
                            ...current,
                            travel: {
                              ...current.travel,
                              companions: Math.min(10, current.travel.companions + 1),
                            },
                          }))
                        }
                        style={styles.counterButton}
                      >
                        <Ionicons color={colors.textPrimary} name="add" size={20} />
                      </Pressable>
                    </View>
                  </View>
                </Section>

                <View style={styles.recommendationBanner}>
                  <View style={styles.bannerIcon}>
                    <Ionicons color={colors.warning} name="sunny" size={28} />
                  </View>
                  <View style={styles.bannerCopy}>
                    <Text style={styles.bannerTitle}>입력한 취향을 반영해</Text>
                    <Text style={styles.bannerText}>우리 아이에게 맞는 여행을 추천해드려요.</Text>
                  </View>
                  <Ionicons color={colors.seaDeep} name="paw" size={34} />
                </View>

                <PrimaryButton
                  icon="paw"
                  label={submitting ? '가입 처리 중...' : '가입 완료하고 시작하기'}
                  onPress={() => void finishSignup()}
                />
              </View>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function StepIntro({ title, description }: { title: string; description: string }) {
  return (
    <View style={styles.intro}>
      <Text style={styles.introTitle}>{title}</Text>
      <Text style={styles.introDescription}>{description}</Text>
    </View>
  );
}

function Section({
  title,
  optional = false,
  children,
}: {
  title: string;
  optional?: boolean;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>
        {title} {optional && <Text style={styles.optional}>(선택)</Text>}
      </Text>
      {children}
    </View>
  );
}

function InfoCard() {
  return (
    <View style={styles.infoCard}>
      <View style={styles.shieldIcon}>
        <Ionicons color={colors.primary} name="shield-checkmark-outline" size={27} />
      </View>
      <View style={styles.infoCopy}>
        <Text style={styles.infoTitle}>안전한 서비스 이용을 위해</Text>
        <Text style={styles.infoText}>회원님의 정보는 안전하게 보호할게요.</Text>
      </View>
      <Ionicons color={colors.primary} name="heart" size={22} />
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  safeArea: { backgroundColor: colors.surface, flex: 1 },
  scrollContent: { flexGrow: 1 },
  screen: {
    alignSelf: 'center',
    maxWidth: 560,
    paddingBottom: 36,
    paddingHorizontal: 24,
    width: '100%',
  },
  submitError: { color: colors.warning, fontSize: 13, marginBottom: 12, textAlign: 'center' },
  intro: { marginBottom: 25 },
  introTitle: { color: colors.textPrimary, fontSize: 25, fontWeight: '900', letterSpacing: -0.8 },
  introDescription: { color: colors.textSecondary, fontSize: 14, lineHeight: 21, marginTop: 8 },
  fieldList: { gap: 13, marginBottom: 20 },
  infoCard: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderColor: colors.primarySoft,
    borderRadius: 16,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 11,
    marginTop: 22,
    minHeight: 82,
    padding: 16,
  },
  shieldIcon: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: 22,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  infoCopy: { flex: 1 },
  infoTitle: { color: colors.textStrong, fontSize: 13, fontWeight: '800' },
  infoText: { color: colors.textSecondary, fontSize: 11, marginTop: 4 },
  section: { gap: 12, marginBottom: 27 },
  sectionTitle: { color: colors.textPrimary, fontSize: 16, fontWeight: '800' },
  optional: { color: colors.textTertiary, fontSize: 12, fontWeight: '500' },
  petTypeGrid: { flexDirection: 'row', gap: 8 },
  speciesDetailInput: {
    backgroundColor: colors.surface,
    borderColor: colors.divider,
    borderRadius: 15,
    borderWidth: 1,
    color: colors.textPrimary,
    fontSize: 14,
    marginTop: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  petTypeCard: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.divider,
    borderRadius: 15,
    borderWidth: 1,
    flex: 1,
    gap: 7,
    justifyContent: 'center',
    minHeight: 89,
    minWidth: 0,
    paddingHorizontal: 4,
  },
  petTypeCardSelected: { backgroundColor: colors.seaSoftLight, borderColor: colors.sea },
  petEmoji: { fontSize: 29 },
  petLabel: { color: colors.textStrong, fontSize: 12, fontWeight: '700' },
  petLabelSelected: { color: colors.seaDeep },
  row: { flexDirection: 'row', gap: 10 },
  wrapRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 9 },
  pressed: { opacity: 0.7 },
  bottomAction: { gap: 10, marginTop: 20 },
  optionalHint: { color: colors.textTertiary, fontSize: 12, textAlign: 'center' },
  departureField: {
    alignItems: 'center',
    borderColor: colors.divider,
    borderRadius: 13,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 9,
    minHeight: 52,
    paddingHorizontal: 15,
  },
  departureInput: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: 14,
    paddingVertical: 12,
  },
  counterRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  counterDescription: { color: colors.textSecondary, fontSize: 13 },
  counter: {
    alignItems: 'center',
    borderColor: colors.divider,
    borderRadius: 22,
    borderWidth: 1,
    flexDirection: 'row',
    height: 44,
  },
  counterButton: { alignItems: 'center', height: 42, justifyContent: 'center', width: 42 },
  counterValue: { color: colors.textPrimary, fontSize: 14, fontWeight: '800', minWidth: 40, textAlign: 'center' },
  recommendationBanner: {
    alignItems: 'center',
    backgroundColor: colors.seaSoftLight,
    borderRadius: 16,
    flexDirection: 'row',
    gap: 11,
    marginBottom: 18,
    padding: 16,
  },
  bannerIcon: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: 22,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  bannerCopy: { flex: 1 },
  bannerTitle: { color: colors.seaDeep, fontSize: 13, fontWeight: '800' },
  bannerText: { color: colors.seaDeep, fontSize: 11, lineHeight: 17, marginTop: 3 },
});
