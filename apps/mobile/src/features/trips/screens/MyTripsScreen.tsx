import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, radius, spacing, typography } from '@/src/theme';

import { ChecklistTab } from '../components/ChecklistTab';
import { DayChips } from '../components/DayChips';
import { MemoTab } from '../components/MemoTab';
import { ScheduleTimeline } from '../components/ScheduleTimeline';
import { TripDistanceSummary } from '../components/TripDistanceSummary';
import { TripSummaryCard } from '../components/TripSummaryCard';
import { TripTabBar } from '../components/TripTabBar';
import { useLatestTrip } from '../hooks/useTrips';
import type { TripDetailTab } from '../types/trip';
import { formatFullDate, getWeatherIcon } from '../utils/tripFormat';

const MAP_TAB_DESCRIPTION = 'Day별 마커와 경로선을 보여주는 지도 탭이 준비 중이에요.';

export function MyTripsScreen() {
  const router = useRouter();
  const { data: trip, isLoading, isError, refetch } = useLatestTrip();

  const [activeTab, setActiveTab] = useState<TripDetailTab>('schedule');
  const [selectedScheduleId, setSelectedScheduleId] = useState<string | null>(null);

  const selectedSchedule = useMemo(() => {
    if (!trip) {
      return null;
    }
    return (
      trip.schedules.find((schedule) => schedule.id === selectedScheduleId) ??
      trip.schedules[0] ??
      null
    );
  }, [trip, selectedScheduleId]);

  const handlePressTripInfo = () => {
    if (!trip) {
      return;
    }
    router.push({ pathname: '/trips/[tripId]/info', params: { tripId: trip.id } });
  };

  const handlePressShare = () => {
    // TODO: 공유하기 바텀시트 연결
    Alert.alert('공유하기', '일정 공유 기능은 다음 작업에서 연결할 예정이에요.');
  };

  const handlePressEdit = () => {
    if (!trip) {
      return;
    }
    router.push({ pathname: '/trips/[tripId]/edit', params: { tripId: trip.id } });
  };

  const handlePressPlace = (placeId: string) => {
    router.push({ pathname: '/places/[placeId]', params: { placeId } });
  };

  const handleToggleSave = (scheduleItemId: string) => {
    // TODO: 저장 토글 Mutation 연결
    Alert.alert('저장', `저장 기능은 API 연동 후 동작해요. (${scheduleItemId})`);
  };

  const handlePressAddSchedule = () => {
    // TODO: 일정 추가(장소 검색) 화면 연결
    router.push('/places');
  };

  if (isLoading) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
          <Text style={styles.stateDescription}>여행 정보를 불러오는 중이에요</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (isError) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.centered}>
          <Text style={styles.stateTitle}>여행 정보를 불러오지 못했어요</Text>
          <Pressable onPress={() => refetch()} style={styles.retryButton}>
            <Text style={styles.retryText}>다시 시도</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  if (!trip) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.centered}>
          <Text style={styles.stateTitle}>저장한 여행이 없어요</Text>
          <Text style={styles.stateDescription}>
            루트 추천에서 마음에 드는 코스를 저장해보세요.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>내 여행</Text>
        <Pressable
          accessibilityLabel="공유하기"
          accessibilityRole="button"
          hitSlop={spacing.sm}
          onPress={handlePressShare}
          style={styles.headerAction}
        >
          <Ionicons color={colors.basalt} name="share-outline" size={20} />
        </Pressable>
      </View>

      <TripSummaryCard onPressInfo={handlePressTripInfo} trip={trip} />
      <TripTabBar activeTab={activeTab} onChangeTab={setActiveTab} />

      {activeTab === 'checklist' && <ChecklistTab />}
      {activeTab === 'memo' && <MemoTab schedules={trip.schedules} />}

      {activeTab === 'map' && (
        <View style={styles.centered}>
          <Text style={styles.stateTitle}>준비 중인 탭이에요</Text>
          <Text style={styles.stateDescription}>{MAP_TAB_DESCRIPTION}</Text>
        </View>
      )}

      {activeTab === 'schedule' && (
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          <DayChips
            onSelectSchedule={setSelectedScheduleId}
            schedules={trip.schedules}
            selectedScheduleId={selectedSchedule?.id ?? ''}
          />

          <TripDistanceSummary summary={trip.distanceSummary} />

          {selectedSchedule && (
            <>
              <View style={styles.dayHeader}>
                <Text style={styles.dayTitle}>Day {selectedSchedule.dayNumber}</Text>
                <Text style={styles.dayDate}>{formatFullDate(selectedSchedule.date)}</Text>
                {selectedSchedule.weather && (
                  <View style={styles.weatherBadge}>
                    <Text style={styles.weatherText}>
                      {getWeatherIcon(selectedSchedule.weather.condition)}{' '}
                      {selectedSchedule.weather.temperature}°
                    </Text>
                  </View>
                )}
                <Pressable
                  accessibilityRole="button"
                  hitSlop={spacing.sm}
                  onPress={handlePressEdit}
                  style={styles.editButton}
                >
                  <Text style={styles.editText}>편집</Text>
                </Pressable>
              </View>

              <ScheduleTimeline
                onPressItem={handlePressPlace}
                onToggleSave={handleToggleSave}
                schedule={selectedSchedule}
              />
            </>
          )}

          <Pressable
            accessibilityRole="button"
            onPress={handlePressAddSchedule}
            style={styles.addButton}
          >
            <Text style={styles.addButtonText}>＋ 일정 추가</Text>
          </Pressable>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    height: 48,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
  },
  headerTitle: {
    color: colors.basalt,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
  },
  headerAction: {
    position: 'absolute',
    right: spacing.md,
  },
  scrollContent: {
    paddingBottom: spacing.xl,
  },
  dayHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    paddingBottom: spacing.xs + 2,
    paddingHorizontal: spacing.lg - 4,
    paddingTop: spacing.md,
  },
  dayTitle: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize - 2,
    fontWeight: '700',
  },
  dayDate: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
  weatherBadge: {
    backgroundColor: '#FFF7DF',
    borderRadius: radius.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  weatherText: {
    color: colors.warning,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
  },
  editButton: {
    marginLeft: 'auto',
  },
  editText: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    fontWeight: '600',
  },
  addButton: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md + 2,
    borderStyle: 'dashed',
    borderWidth: 1.5,
    marginHorizontal: spacing.lg - 4,
    marginTop: spacing.sm,
    paddingVertical: spacing.sm + 2,
  },
  addButtonText: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  centered: {
    alignItems: 'center',
    flex: 1,
    gap: spacing.sm,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  stateTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  stateDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    textAlign: 'center',
  },
  retryButton: {
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  retryText: {
    color: colors.primary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
});
