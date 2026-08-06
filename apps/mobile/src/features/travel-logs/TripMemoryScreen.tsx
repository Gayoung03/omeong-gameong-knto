import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState, useMemo } from 'react';
import { FlatList, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { IconButton } from '@/src/components/ui/IconButton';
import { colors, spacing, typography } from '@/src/theme';
import { formatDateRangeLabel } from './utils/dateFormat';
import { groupLogsByDate } from './utils/groupLogsByDate';
import { useTripMemoryLogs } from './hooks/useTripMemoryLogs';
import { DateMemorySection } from './components/DateMemorySection';
import { MemoryPhotoModal } from './components/MemoryPhotoModal';
import { MemoryCardSkeleton } from './components/MemoryCardSkeleton';

export function TripMemoryScreen() {
  const router = useRouter();
  const { tripId } = useLocalSearchParams<{ tripId: string }>();
  const { trip, logs, isPending } = useTripMemoryLogs(tripId ?? '');
  const [selectedLogId, setSelectedLogId] = useState<string | undefined>();
  const selectedLog = useMemo(
    () => logs?.find((log) => log.logId === selectedLogId),
    [logs, selectedLogId],
  );
  const groups = useMemo(() => (logs ? groupLogsByDate(logs) : []), [logs]);

  if (!tripId) {
    return null;
  }

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <View style={styles.header}>
        <IconButton
          accessibilityLabel="뒤로 가기"
          icon="chevron-back"
          onPress={() => router.back()}
        />
        {trip && (
          <View style={styles.headerInfo}>
            <Text style={styles.title}>{trip.title}</Text>
            <Text style={styles.period}>
              {formatDateRangeLabel({ start: trip.startDate, end: trip.endDate })} · {trip.logCount}
              개의 순간
            </Text>
          </View>
        )}
      </View>

      {isPending ? (
        <ScrollView contentContainerStyle={styles.content}>
          {Array.from({ length: 3 }).map((_, i) => (
            <View key={i} style={styles.section}>
              <MemoryCardSkeleton size="large" />
              <View style={styles.grid}>
                <MemoryCardSkeleton size="small" />
                <MemoryCardSkeleton size="small" />
              </View>
            </View>
          ))}
        </ScrollView>
      ) : groups.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyTitle}>아직 이 여행에 남겨진 순간이 없어요</Text>
          <Text style={styles.emptyDesc}>반려동물과 함께한 소중한 순간을 남겨보세요</Text>
        </View>
      ) : (
        <FlatList
          contentContainerStyle={styles.content}
          data={groups}
          keyboardDismissMode="on-drag"
          keyExtractor={(group) => group.date}
          renderItem={({ item }) => (
            <DateMemorySection group={item} onSelectLog={setSelectedLogId} />
          )}
          showsVerticalScrollIndicator={false}
        />
      )}

      <MemoryPhotoModal log={selectedLog} onClose={() => setSelectedLogId(undefined)} tripId={tripId} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: spacing.lg,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  empty: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    padding: spacing.lg,
  },
  emptyDesc: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  emptyTitle: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
    textAlign: 'center',
  },
  grid: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  headerInfo: {
    flex: 1,
  },
  period: {
    color: colors.textSecondary,
    fontSize: typography.body.fontSize - 3,
    marginTop: spacing.xs,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  section: {
    gap: spacing.sm,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
});
