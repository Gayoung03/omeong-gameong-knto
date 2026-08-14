import { forwardRef } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { Schedule, Trip } from '../types/trip';
import {
  formatMonthDay,
  formatPets,
  formatTripPeriod,
  getTransportLabel,
  getWeatherIcon,
} from '../utils/tripFormat';

type TripShareCardProps = {
  trip: Trip;
  /** 카드에 담을 날짜들. 전체 저장이면 trip.schedules 전부 */
  schedules: Schedule[];
};

/**
 * 이미지로 저장·공유할 때 캡처하는 카드.
 * 화면용 컴포넌트를 그대로 찍지 않고 별도 레이아웃을 쓴다
 * (버튼·탭 같은 조작 UI가 이미지에 들어가면 안 되기 때문).
 */
export const TripShareCard = forwardRef<View, TripShareCardProps>(function TripShareCard(
  { trip, schedules },
  ref,
) {
  return (
    <View collapsable={false} ref={ref} style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.emoji}>{trip.coverEmoji}</Text>
        <Text style={styles.title}>{trip.title}</Text>
        <Text style={styles.period}>{formatTripPeriod(trip)}</Text>
        <Text style={styles.tags}>
          {getTransportLabel(trip.transport)} · {formatPets(trip.pets)}
        </Text>
      </View>

      {schedules.map((schedule) => (
        <View key={schedule.id} style={styles.daySection}>
          <View style={styles.dayHeader}>
            <Text style={styles.dayTitle}>Day {schedule.dayNumber}</Text>
            <Text style={styles.dayDate}>{formatMonthDay(schedule.date)}</Text>
            {schedule.weather && (
              <Text style={styles.dayWeather}>
                {getWeatherIcon(schedule.weather.condition)} {schedule.weather.temperature}°
              </Text>
            )}
          </View>

          {schedule.items.length === 0 ? (
            <Text style={styles.emptyText}>등록된 일정이 없어요</Text>
          ) : (
            schedule.items.map((item) => (
              <View key={item.id} style={styles.itemRow}>
                <View style={styles.orderBadge}>
                  <Text style={styles.orderText}>{item.order}</Text>
                </View>
                <Text numberOfLines={1} style={styles.placeName}>
                  {item.place.name}
                </Text>
              </View>
            ))
          )}
        </View>
      ))}

      <Text style={styles.footer}>오멍가멍 · 반려동물과 함께하는 제주 여행</Text>
    </View>
  );
});

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    paddingBottom: spacing.lg,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    width: 340,
  },
  header: {
    alignItems: 'center',
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    gap: spacing.xs,
    paddingBottom: spacing.md,
  },
  emoji: {
    fontSize: 34,
  },
  title: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: typography.sectionTitle.fontWeight,
    textAlign: 'center',
  },
  period: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
  },
  tags: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
  },
  daySection: {
    borderBottomColor: colors.border,
    borderBottomWidth: 1,
    paddingBottom: spacing.sm + 4,
    paddingTop: spacing.md,
  },
  dayHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  dayTitle: {
    color: colors.leaf,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  dayDate: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
  },
  dayWeather: {
    color: colors.textSecondary,
    fontSize: typography.micro.fontSize,
    marginLeft: 'auto',
  },
  itemRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    paddingVertical: spacing.xs + 1,
  },
  orderBadge: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.full,
    height: 20,
    justifyContent: 'center',
    width: 20,
  },
  orderText: {
    color: colors.primary,
    fontSize: typography.micro.fontSize - 1,
    fontWeight: '700',
  },
  placeName: {
    color: colors.textPrimary,
    flex: 1,
    fontSize: typography.label.fontSize,
    fontWeight: '600',
  },
  emptyText: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    paddingVertical: spacing.xs,
  },
  footer: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize - 1,
    paddingTop: spacing.md,
    textAlign: 'center',
  },
});
