import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/src/theme';
import type { TravelLog } from '@/src/types/travelLog';

import { formatShortDate } from '../utils/dateFormat';

type MemoryCardBackProps = {
  log: TravelLog;
  /** 없으면 수정 버튼을 숨긴다. 저장 전(완성 화면)에는 수정 대상 기록이 아직 없기 때문. */
  onEditPress?: () => void;
};

/**
 * 팝업 뒷면: 실제 인화 사진 뒷면처럼 나의 한 줄을 가장 크게, 날짜·장소는 아래에 작고 차분하게.
 * 정보 카드 구조(제목·아이콘 목록·구분선)는 의도적으로 쓰지 않는다.
 */
export function MemoryCardBack({ log, onEditPress }: MemoryCardBackProps) {
  const hasMessage = Boolean(log.personalMessage?.trim());

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        {hasMessage ? (
          <Text style={styles.message}>{log.personalMessage}</Text>
        ) : (
          <Text style={styles.prompt}>이 순간에 한 줄을 남겨보세요</Text>
        )}

        <Ionicons color={colors.border} name="paw" size={14} style={styles.decoration} />

        <Text style={styles.meta}>
          {formatShortDate(log.recordedDate)} · {log.placeName}
        </Text>
      </View>

      {onEditPress ? (
        <Pressable
          accessibilityLabel={hasMessage ? '한 줄 기록 수정' : '한 줄 기록 남기기'}
          accessibilityRole="button"
          hitSlop={spacing.sm}
          onPress={onEditPress}
          style={styles.editButton}
        >
          <Ionicons color={colors.sea} name="create-outline" size={13} />
          <Text style={styles.editLabel}>{hasMessage ? '한 줄 기록 수정' : '한 줄 기록 남기기'}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'space-between',
    paddingBottom: spacing.md,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
  },
  content: {
    alignItems: 'center',
    flex: 1,
    gap: spacing.md,
    justifyContent: 'center',
  },
  decoration: {
    marginVertical: spacing.xs,
  },
  editButton: {
    alignItems: 'center',
    alignSelf: 'center',
    flexDirection: 'row',
    gap: spacing.xs / 2,
  },
  editLabel: {
    color: colors.sea,
    fontSize: typography.body.fontSize - 3,
    fontWeight: '600',
  },
  message: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize + 1,
    fontWeight: '700',
    lineHeight: (typography.body.fontSize + 1) * 1.5,
    textAlign: 'center',
  },
  meta: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  prompt: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize,
    textAlign: 'center',
  },
});
