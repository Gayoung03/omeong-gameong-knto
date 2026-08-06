import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/src/theme';

import { formatDayTitle } from '../utils/dateFormat';
import type { DateMemoryGroup } from '../utils/groupLogsByDate';
import { MemoryLogCard } from './MemoryLogCard';

type DateMemorySectionProps = {
  group: DateMemoryGroup;
  onSelectLog: (logId: string) => void;
};

/** 날짜 제목에는 지역명을 넣지 않는다. 같은 날짜라도 장소가 다르면 개별 카드로 늘어놓는다. */
export function DateMemorySection({ group, onSelectLog }: DateMemorySectionProps) {
  return (
    <View style={styles.section}>
      <Text style={styles.dateTitle}>{formatDayTitle(group.date)}</Text>

      <MemoryLogCard log={group.representativeLog} onPress={onSelectLog} size="large" />

      {group.otherLogs.length > 0 ? (
        <View style={styles.grid}>
          {group.otherLogs.map((log) => (
            <View key={log.logId} style={styles.gridItem}>
              <MemoryLogCard log={log} onPress={onSelectLog} size="small" />
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  dateTitle: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  gridItem: {
    width: '47%',
  },
  section: {
    gap: spacing.sm,
  },
});
