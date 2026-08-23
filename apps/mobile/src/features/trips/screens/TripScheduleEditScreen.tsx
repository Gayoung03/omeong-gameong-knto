import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import DraggableFlatList, { type RenderItemParams } from 'react-native-draggable-flatlist';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ErrorState } from '@/src/components/feedback/ErrorState';
import { colors, spacing, typography } from '@/src/theme';

import { DayChips } from '../components/DayChips';
import { ScheduleEditRow } from '../components/ScheduleEditRow';
import { ScheduleItemActionSheet } from '../components/ScheduleItemActionSheet';
import { useSaveSchedule } from '../hooks/useSaveSchedule';
import { useScheduleEdit } from '../hooks/useScheduleEdit';
import { useTrip } from '../hooks/useTrips';
import type { ScheduleItem, Trip } from '../types/trip';

type TripScheduleEditScreenProps = {
  tripId: string;
};

export function TripScheduleEditScreen({ tripId }: TripScheduleEditScreenProps) {
  const { data: trip, isLoading, isError, refetch } = useTrip(tripId);

  if (isLoading) {
    return (
      <SafeAreaView edges={['top']} style={styles.safeArea}>
        <EditHeader />
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (isError || !trip) {
    return (
      <SafeAreaView edges={['top']} style={styles.safeArea}>
        <EditHeader />
        <ErrorState onRetry={() => refetch()} />
      </SafeAreaView>
    );
  }

  // 여행 데이터를 다 받은 뒤에 마운트해야 편집 상태의 초기값이 제대로 잡힌다
  return <TripScheduleEditContent trip={trip} />;
}

type EditHeaderProps = {
  onPressCancel?: () => void;
  onPressSave?: () => void;
  canSave?: boolean;
};

function EditHeader({ onPressCancel, onPressSave, canSave = false }: EditHeaderProps) {
  return (
    <View style={styles.header}>
      {onPressCancel ? (
        <Pressable
          accessibilityRole="button"
          hitSlop={spacing.sm}
          onPress={onPressCancel}
          style={styles.headerSide}
        >
          <Text style={styles.cancelText}>취소</Text>
        </Pressable>
      ) : (
        <View style={styles.headerSide} />
      )}

      <Text style={styles.headerTitle}>일정 편집</Text>

      {onPressSave ? (
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ disabled: !canSave }}
          disabled={!canSave}
          hitSlop={spacing.sm}
          onPress={onPressSave}
          style={[styles.headerSide, styles.headerRight]}
        >
          <Text style={[styles.saveText, !canSave && styles.disabledText]}>저장</Text>
        </Pressable>
      ) : (
        <View style={styles.headerSide} />
      )}
    </View>
  );
}

type TripScheduleEditContentProps = {
  trip: Trip;
};

function TripScheduleEditContent({ trip }: TripScheduleEditContentProps) {
  const router = useRouter();
  const {
    draftSchedules,
    selectedSchedule,
    selectedScheduleId,
    selectSchedule,
    isDirty,
    reorderItems,
    removeItem,
    moveItemToSchedule,
  } = useScheduleEdit(trip.schedules);
  const saveSchedule = useSaveSchedule(trip.id);

  const [actionItemId, setActionItemId] = useState<string | null>(null);

  const actionItem = selectedSchedule?.items.find((item) => item.id === actionItemId) ?? null;

  const handlePressCancel = () => {
    if (!isDirty) {
      router.back();
      return;
    }

    Alert.alert('편집을 취소할까요?', '저장하지 않은 변경 사항이 사라져요.', [
      { text: '계속 편집', style: 'cancel' },
      { text: '취소하고 나가기', style: 'destructive', onPress: () => router.back() },
    ]);
  };

  const handlePressSave = () => {
    saveSchedule.mutate(
      { draft: draftSchedules, original: trip.schedules },
      {
        onError: () => {
          // 실패했을 때 화면을 닫으면 사용자는 저장된 줄 안다. 편집 상태로 남긴다.
          Alert.alert('저장하지 못했어요', '잠시 후 다시 시도해 주세요.');
        },
        onSuccess: () => router.back(),
      },
    );
  };

  const handleRemove = () => {
    if (!selectedSchedule || !actionItem) {
      return;
    }
    removeItem(selectedSchedule.id, actionItem.id);
    setActionItemId(null);
  };

  const handleMoveToSchedule = (toScheduleId: string) => {
    if (!selectedSchedule || !actionItem) {
      return;
    }
    moveItemToSchedule(selectedSchedule.id, actionItem.id, toScheduleId);
    setActionItemId(null);
  };

  const renderItem = ({ item, drag, isActive }: RenderItemParams<ScheduleItem>) => (
    <ScheduleEditRow
      isActive={isActive}
      item={item}
      onDragStart={drag}
      onPressMore={setActionItemId}
    />
  );

  return (
    <SafeAreaView edges={['top']} style={styles.safeArea}>
      <EditHeader
        canSave={isDirty && !saveSchedule.isPending}
        onPressCancel={handlePressCancel}
        onPressSave={handlePressSave}
      />

      <DayChips
        onSelectSchedule={selectSchedule}
        schedules={draftSchedules}
        selectedScheduleId={selectedScheduleId}
      />

      <View style={styles.hint}>
        <Ionicons color={colors.textTertiary} name="information-circle-outline" size={14} />
        <Text style={styles.hintText}>
          왼쪽 손잡이를 길게 눌러 끌면 순서가 바뀌어요. 오른쪽 버튼으로 날짜를 옮기거나 삭제할 수
          있어요.
        </Text>
      </View>

      {selectedSchedule && selectedSchedule.items.length > 0 ? (
        <DraggableFlatList
          containerStyle={styles.listContainer}
          contentContainerStyle={styles.listContent}
          data={selectedSchedule.items}
          keyExtractor={(item) => item.id}
          onDragEnd={({ data }) => reorderItems(selectedSchedule.id, data)}
          renderItem={renderItem}
        />
      ) : (
        <View style={styles.centered}>
          <Text style={styles.stateTitle}>이 날짜에는 일정이 없어요</Text>
          <Text style={styles.stateDescription}>
            다른 Day에서 일정을 옮겨오거나 새로 추가해보세요.
          </Text>
        </View>
      )}

      {actionItem && selectedSchedule && (
        <ScheduleItemActionSheet
          currentScheduleId={selectedSchedule.id}
          onClose={() => setActionItemId(null)}
          onMoveToSchedule={handleMoveToSchedule}
          onRemove={handleRemove}
          placeName={actionItem.place.name}
          schedules={draftSchedules}
        />
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
    height: 56,
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
  },
  headerSide: {
    minWidth: 48,
  },
  headerRight: {
    alignItems: 'flex-end',
  },
  headerTitle: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: typography.sectionTitle.fontWeight,
    includeFontPadding: false,
    lineHeight: 24,
  },
  cancelText: {
    color: colors.textSecondary,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
  },
  saveText: {
    color: colors.primary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  disabledText: {
    color: colors.textTertiary,
  },
  hint: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.xs + 2,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm + 2,
  },
  hintText: {
    color: colors.textTertiary,
    flex: 1,
    fontSize: typography.micro.fontSize,
    lineHeight: 16,
  },
  listContainer: {
    flex: 1,
  },
  listContent: {
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.md,
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
});
