import Ionicons from '@expo/vector-icons/Ionicons';
import { useEffect } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ScreenHeader } from '@/src/components/ui/ScreenHeader';
import { colors, spacing, typography } from '@/src/theme';

import { NotificationSettingRow } from './components/NotificationSettingRow';
import { useNotificationPreferencesStore } from './stores/useNotificationPreferencesStore';

/**
 * 알림 수신 여부만 관리하는 화면이다.
 * TODO: 1:1 문의 답변 푸시 흐름(답변 등록 → inquiryAnswerEnabled 확인 → 토큰 조회 → 발송 →
 *       알림 탭 시 /inquiries/{id}로 이동)도 서버 연동 시점에 붙인다.
 */
export function NotificationSettingsScreen() {
  const { preferences, isLoading, saveErrorMessage, load, setPreference } =
    useNotificationPreferencesStore();

  // 화면에 다시 들어올 때마다 저장된 값을 읽어 온다.
  useEffect(() => {
    void load();
  }, [load]);

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <ScreenHeader title="알림 설정" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.sectionLabel}>알림 항목</Text>

        <NotificationSettingRow
          disabled={isLoading}
          label="1:1 문의 답변 알림"
          onValueChange={(next) => void setPreference('inquiryAnswerEnabled', next)}
          value={preferences.inquiryAnswerEnabled}
        />
        <NotificationSettingRow
          disabled={isLoading}
          label="마케팅 및 이벤트 알림"
          onValueChange={(next) => void setPreference('marketingEnabled', next)}
          value={preferences.marketingEnabled}
        />

        {saveErrorMessage ? <Text style={styles.saveError}>{saveErrorMessage}</Text> : null}

        <View style={styles.notice}>
          <Ionicons color={colors.iconGray} name="information-circle-outline" size={16} />
          <Text style={styles.noticeText}>
            일부 알림은 기기의 알림 권한 설정에 따라 수신되지 않을 수 있어요.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  notice: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingTop: spacing.xl,
  },
  noticeText: {
    color: colors.textSecondary,
    flex: 1,
    fontSize: typography.body.fontSize - 3,
    lineHeight: 20,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  saveError: {
    color: colors.error,
    fontSize: typography.body.fontSize - 3,
    paddingTop: spacing.md,
  },
  sectionLabel: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 2,
    paddingBottom: spacing.sm,
  },
});
