import { StyleSheet, Text, View } from 'react-native';

import { Card } from '@/src/components/ui/Card';
import { colors, spacing, typography } from '@/src/theme';
import type { UngroupedLogGroup } from '@/src/types/travelLog';

import { formatMonthLabel } from '../utils/dateFormat';
import { PhotoCollage } from './PhotoCollage';

type UngroupedLogCardProps = {
  group: UngroupedLogGroup;
};

/** 여행 일정에 연결되지 않은 개별 기록을 월 단위로 묶어 보여준다. */
export function UngroupedLogCard({ group }: UngroupedLogCardProps) {
  return (
    <Card padding="sm" style={styles.card}>
      <View style={styles.titleRow}>
        <Text style={styles.title}>소소한 제주 기록</Text>
      </View>

      <Text style={styles.meta}>
        {formatMonthLabel(group.year, group.month)} · {group.logCount}개의 순간
      </Text>

      <PhotoCollage logs={group.previewLogs} />
    </Card>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: spacing.sm,
  },
  meta: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});
