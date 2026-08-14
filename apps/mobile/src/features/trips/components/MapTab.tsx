import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '@/src/theme';

import type { Schedule } from '../types/trip';
import { DayChips } from './DayChips';
import { MapPlaceCard } from './MapPlaceCard';
import { TripMapView } from './TripMapView';

type MapTabProps = {
  schedules: Schedule[];
  onPressPlace: (placeId: string) => void;
};

/** 내 여행 > 지도 탭. Day별 마커·경로선과 선택한 장소 카드를 보여준다 */
export function MapTab({ schedules, onPressPlace }: MapTabProps) {
  const [selectedScheduleId, setSelectedScheduleId] = useState(schedules[0]?.id ?? '');
  // 처음에는 첫 번째 방문지를 보여준다
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(
    schedules[0]?.items[0]?.place.id ?? null,
  );

  const selectedSchedule =
    schedules.find((schedule) => schedule.id === selectedScheduleId) ?? schedules[0] ?? null;

  const selectedItem =
    selectedSchedule?.items.find((item) => item.place.id === selectedPlaceId) ?? null;

  /**
   * 지도를 그릴 때 강조할 장소. 날짜가 바뀔 때만 달라져야 한다.
   * 선택 중인 장소를 그대로 넘기면 마커를 누를 때마다 지도가 다시 그려진다.
   */
  const initialSelectedPlaceId = selectedSchedule?.items[0]?.place.id ?? null;

  const handleSelectSchedule = (scheduleId: string) => {
    const nextSchedule = schedules.find((schedule) => schedule.id === scheduleId);
    setSelectedPlaceId(nextSchedule?.items[0]?.place.id ?? null);
    setSelectedScheduleId(scheduleId);
  };

  if (!selectedSchedule) {
    return (
      <View style={styles.centered}>
        <Text style={styles.stateTitle}>표시할 일정이 없어요</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <DayChips
        onSelectSchedule={handleSelectSchedule}
        schedules={schedules}
        selectedScheduleId={selectedSchedule.id}
      />

      <View style={styles.mapArea}>
        {selectedSchedule.items.length === 0 ? (
          <View style={styles.centered}>
            <Text style={styles.stateTitle}>이 날짜에는 일정이 없어요</Text>
            <Text style={styles.stateDescription}>일정을 추가하면 지도에 경로가 그려져요.</Text>
          </View>
        ) : (
          <TripMapView
            initialSelectedPlaceId={initialSelectedPlaceId}
            items={selectedSchedule.items}
            onSelectPlace={setSelectedPlaceId}
            redrawKey={selectedSchedule.id}
          />
        )}
      </View>

      {selectedItem && (
        <MapPlaceCard
          item={selectedItem}
          onClose={() => setSelectedPlaceId(null)}
          onPressDetail={onPressPlace}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  mapArea: {
    flex: 1,
    marginTop: spacing.sm,
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
