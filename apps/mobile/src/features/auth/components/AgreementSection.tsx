import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { SignupAgreements } from '../types/auth';
import { AgreementRow } from './AgreementRow';

/** 마케팅 수신을 뺀 나머지는 모두 동의해야 가입을 진행할 수 있다. */
const REQUIRED_KEYS = ['age14', 'terms', 'privacy'] as const;

export function hasAllRequiredAgreements(agreements: SignupAgreements) {
  return REQUIRED_KEYS.every((key) => agreements[key]);
}

type AgreementSectionProps = {
  value: SignupAgreements;
  onChange: (next: SignupAgreements) => void;
  error?: string;
};

export function AgreementSection({ value, onChange, error }: AgreementSectionProps) {
  const router = useRouter();

  const allChecked = Object.values(value).every(Boolean);

  const toggleAll = () => {
    const next = !allChecked;
    onChange({ age14: next, terms: next, privacy: next, marketing: next });
  };

  const toggle = (key: keyof SignupAgreements) => {
    onChange({ ...value, [key]: !value[key] });
  };

  return (
    <View style={[styles.container, Boolean(error) && styles.containerError]}>
      <AgreementRow
        checked={allChecked}
        emphasized
        label="약관에 모두 동의합니다"
        onToggle={toggleAll}
      />

      <View style={styles.divider} />

      <AgreementRow
        checked={value.age14}
        label="만 14세 이상입니다"
        onToggle={() => toggle('age14')}
        requirement="required"
      />
      <AgreementRow
        checked={value.terms}
        label="서비스 이용약관 동의"
        onPressDetail={() => router.push('/legal/terms')}
        onToggle={() => toggle('terms')}
        requirement="required"
      />
      <AgreementRow
        checked={value.privacy}
        label="개인정보처리방침 동의"
        onPressDetail={() => router.push('/legal/privacy')}
        onToggle={() => toggle('privacy')}
        requirement="required"
      />
      <AgreementRow
        checked={value.marketing}
        label="마케팅 정보 수신 동의"
        onToggle={() => toggle('marketing')}
        requirement="optional"
      />

      {Boolean(error) && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  containerError: {
    borderColor: colors.primary,
  },
  divider: {
    backgroundColor: colors.border,
    height: 1,
    marginBottom: spacing.xs,
  },
  error: {
    color: colors.primary,
    fontSize: typography.caption.fontSize,
    paddingBottom: spacing.sm,
    paddingTop: spacing.xs,
  },
});
