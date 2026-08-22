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

import { IconButton } from '@/src/components/ui/IconButton';
import { colors, radius, spacing, typography } from '@/src/theme';

import { ChecklistTab } from '../components/ChecklistTab';
import { DayChips } from '../components/DayChips';
import { MapTab } from '../components/MapTab';
import { MemoTab } from '../components/MemoTab';
import { ScheduleTimeline } from '../components/ScheduleTimeline';
import { TripDistanceSummary } from '../components/TripDistanceSummary';
import { TripImagePreviewModal } from '../components/TripImagePreviewModal';
import { TripShareSheet } from '../components/TripShareSheet';
import { TripSummaryCard } from '../components/TripSummaryCard';
import { TripTabBar } from '../components/TripTabBar';
import { WeatherSheet } from '../components/WeatherSheet';
import { useTripShare } from '../hooks/useTripShare';
import { useTrip } from '../hooks/useTrips';
import type { TripDetailTab } from '../types/trip';
import { formatFullDate, getWeatherIcon } from '../utils/tripFormat';

/** 이미지로 만들 범위 */
type ShareImageTarget = 'wholeTrip' | 'day';

/**
 * 바텀시트가 닫히는 애니메이션이 끝난 뒤 실행한다.
 * iOS 는 모달이 닫히는 도중에 OS 공유 창을 띄우면 조용히 무시한다.
 */
const SHEET_CLOSE_DELAY_MS = 350;

function runAfterSheetClose(action: () => void) {
  setTimeout(action, SHEET_CLOSE_DELAY_MS);
}

export function TripDetailScreen({ tripId }: { tripId: string }) {
  const router = useRouter();
  const { data: trip, isLoading, isError, refetch } = useTrip(tripId);

  const [activeTab, setActiveTab] = useState<TripDetailTab>('schedule');
  const [selectedScheduleId, setSelectedScheduleId] = useState<string | null>(null);
  const [isWeatherSheetOpen, setIsWeatherSheetOpen] = useState(false);
  const [isShareSheetOpen, setIsShareSheetOpen] = useState(false);
  const [shareImageTarget, setShareImageTarget] = useState<ShareImageTarget | null>(null);

  const { isSaving, copyLink, shareLink, saveImage, shareImage } = useTripShare({ trip });

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

  const handleBack = () => {
    if (router.canGoBack()) {
      router.back();
      return;
    }
    router.replace('/trips');
  };

  const handlePressTripInfo = () => {
    if (!trip) {
      return;
    }
    router.push({ pathname: '/trips/[tripId]/info', params: { tripId: trip.id } });
  };

  const handlePressShare = () => {
    setIsShareSheetOpen(true);
  };

  const handleCopyLink = () => {
    setIsShareSheetOpen(false);
    runAfterSheetClose(() => void copyLink());
  };

  const handleShareLink = () => {
    setIsShareSheetOpen(false);
    runAfterSheetClose(() => void shareLink());
  };

  const handleOpenImagePreview = (target: ShareImageTarget) => {
    setIsShareSheetOpen(false);
    runAfterSheetClose(() => setShareImageTarget(target));
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
    if (!trip) {
      return;
    }

    router.push({
      pathname: '/trips/[tripId]/add-schedule',
      // 보고 있던 날짜에 바로 담을 수 있도록 함께 넘긴다
      params: { tripId: trip.id, scheduleId: selectedSchedule?.id ?? '' },
    });
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
          <Text style={styles.stateTitle}>여행을 찾을 수 없어요</Text>
          <Pressable onPress={handleBack} style={styles.retryButton}>
            <Text style={styles.retryText}>목록으로</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <View style={styles.header}>
        <IconButton accessibilityLabel="뒤로 가기" icon="chevron-back" onPress={handleBack} />
        <Text numberOfLines={1} style={styles.headerTitle}>
          {trip.title}
        </Text>
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

      {activeTab === 'map' && <MapTab onPressPlace={handlePressPlace} schedules={trip.schedules} />}

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
                  <Pressable
                    accessibilityHint="시간대별 예보와 반려동물 산책 팁을 볼 수 있어요"
                    accessibilityLabel={`Day ${selectedSchedule.dayNumber} 날씨 자세히 보기`}
                    accessibilityRole="button"
                    hitSlop={spacing.xs}
                    onPress={() => setIsWeatherSheetOpen(true)}
                    style={styles.weatherBadge}
                  >
                    <Text style={styles.weatherText}>
                      {getWeatherIcon(selectedSchedule.weather.condition)}{' '}
                      {selectedSchedule.weather.temperature}°
                    </Text>
                    <Ionicons color={colors.warning} name="chevron-forward" size={11} />
                  </Pressable>
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

      {isWeatherSheetOpen && selectedSchedule?.weather && (
        <WeatherSheet
          date={selectedSchedule.date}
          dayNumber={selectedSchedule.dayNumber}
          onClose={() => setIsWeatherSheetOpen(false)}
          weather={selectedSchedule.weather}
        />
      )}

      {isShareSheetOpen && (
        <TripShareSheet
          hasSchedules={trip.schedules.length > 0}
          onClose={() => setIsShareSheetOpen(false)}
          onPressCopyLink={handleCopyLink}
          onPressSaveByDay={() => handleOpenImagePreview('day')}
          onPressSaveWholeTrip={() => handleOpenImagePreview('wholeTrip')}
          onPressShareLink={handleShareLink}
        />
      )}

      {shareImageTarget && (
        <TripImagePreviewModal
          initialScheduleId={selectedSchedule?.id ?? ''}
          isSaving={isSaving}
          mode={shareImageTarget}
          onClose={() => setShareImageTarget(null)}
          onSave={saveImage}
          onShare={shareImage}
          trip={trip}
        />
      )}
    </SafeAreaView>
  );
}

const HEADER_ACTION_SIZE = 44;

const styles = StyleSheet.create({
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    paddingHorizontal: spacing.sm,
  },
  headerTitle: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
    textAlign: 'center',
  },
  headerAction: {
    alignItems: 'center',
    height: HEADER_ACTION_SIZE,
    justifyContent: 'center',
    width: HEADER_ACTION_SIZE,
  },
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
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
    alignItems: 'center',
    backgroundColor: colors.leafSoft,
    borderRadius: radius.full,
    flexDirection: 'row',
    gap: 1,
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
