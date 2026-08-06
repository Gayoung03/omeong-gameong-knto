import {
  BottomSheetBackdrop,
  BottomSheetModal,
  BottomSheetView,
  type BottomSheetBackdropProps,
} from '@gorhom/bottom-sheet';
import { forwardRef, useCallback, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Calendar, LocaleConfig, type DateData } from 'react-native-calendars';

import { Button } from '@/src/components/ui/Button';
import { Chip, ChipRow } from '@/src/components/ui/Chip';
import { colors, radius, spacing, typography } from '@/src/theme';
import type { DateRange } from '@/src/types/travelLog';

import {
  eachDayInRange,
  getCurrentMonthRange,
  getRecentThreeMonthsRange,
} from '../utils/dateFormat';

LocaleConfig.locales.ko = {
  monthNames: [
    '1월',
    '2월',
    '3월',
    '4월',
    '5월',
    '6월',
    '7월',
    '8월',
    '9월',
    '10월',
    '11월',
    '12월',
  ],
  monthNamesShort: [
    '1월',
    '2월',
    '3월',
    '4월',
    '5월',
    '6월',
    '7월',
    '8월',
    '9월',
    '10월',
    '11월',
    '12월',
  ],
  dayNames: ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일'],
  dayNamesShort: ['일', '월', '화', '수', '목', '금', '토'],
  today: '오늘',
};
LocaleConfig.defaultLocale = 'ko';

type QuickPreset = 'all' | 'thisMonth' | 'recentThreeMonths' | 'custom';

export type FilterSheetHandle = {
  open: () => void;
};

type DateFilterBottomSheetProps = {
  value: DateRange | null;
  onApply: (range: DateRange | null) => void;
};

export const DateFilterBottomSheet = forwardRef<FilterSheetHandle, DateFilterBottomSheetProps>(
  function DateFilterBottomSheet({ value, onApply }, ref) {
    const sheetRef = useRef<BottomSheetModal>(null);
    const [pendingRange, setPendingRange] = useState<DateRange | null>(value);
    const [preset, setPreset] = useState<QuickPreset>(value ? 'custom' : 'all');

    useImperativeHandle(
      ref,
      () => ({
        open: () => {
          // 시트를 열 때마다 적용된 값으로 되돌려, 닫았다 열어도 선택 상태가 유지되게 한다.
          setPendingRange(value);
          setPreset(value ? 'custom' : 'all');
          sheetRef.current?.present();
        },
      }),
      [value],
    );

    const handleApply = useCallback(() => {
      onApply(pendingRange);
      sheetRef.current?.dismiss();
    }, [onApply, pendingRange]);

    const markedDates = useMemo(() => buildMarkedDates(pendingRange), [pendingRange]);

    const handleDayPress = useCallback((day: DateData) => {
      setPreset('custom');
      setPendingRange((current) => {
        // 시작일만 선택된 상태에서 이후 날짜를 누르면 기간이 완성되고,
        // 그 외에는 누른 날짜부터 다시 선택을 시작한다.
        if (current && current.start === current.end && day.dateString >= current.start) {
          return { start: current.start, end: day.dateString };
        }

        return { start: day.dateString, end: day.dateString };
      });
    }, []);

    const selectPreset = useCallback((next: QuickPreset) => {
      setPreset(next);

      if (next === 'all') {
        setPendingRange(null);
        return;
      }

      if (next === 'thisMonth') {
        setPendingRange(getCurrentMonthRange());
        return;
      }

      if (next === 'recentThreeMonths') {
        setPendingRange(getRecentThreeMonthsRange());
      }
    }, []);

    const renderBackdrop = useCallback(
      (props: BottomSheetBackdropProps) => (
        <BottomSheetBackdrop {...props} appearsOnIndex={0} disappearsOnIndex={-1} />
      ),
      [],
    );

    return (
      <BottomSheetModal
        backdropComponent={renderBackdrop}
        enableDynamicSizing={false}
        enablePanDownToClose
        ref={sheetRef}
        snapPoints={['82%']}
      >
        <BottomSheetView style={styles.sheet}>
          <Text style={styles.title}>날짜 선택</Text>

          <ChipRow>
            <Chip
              label="전체 날짜"
              onPress={() => selectPreset('all')}
              selected={preset === 'all'}
              tone="orange"
            />
            <Chip
              label="이번 달"
              onPress={() => selectPreset('thisMonth')}
              selected={preset === 'thisMonth'}
              tone="mint"
            />
            <Chip
              label="최근 3개월"
              onPress={() => selectPreset('recentThreeMonths')}
              selected={preset === 'recentThreeMonths'}
              tone="mint"
            />
          </ChipRow>

          <View style={styles.calendarWrapper}>
            <Calendar
              current={pendingRange?.start}
              markedDates={markedDates}
              markingType="period"
              monthFormat="yyyy년 M월"
              onDayPress={handleDayPress}
              theme={calendarTheme}
            />
          </View>

          <View style={styles.footer}>
            <View style={styles.footerButton}>
              <Button
                label="초기화"
                onPress={() => {
                  setPendingRange(null);
                  setPreset('all');
                }}
                variant="outline"
              />
            </View>
            <View style={styles.footerButton}>
              <Button label="적용" onPress={handleApply} variant="primary" />
            </View>
          </View>
        </BottomSheetView>
      </BottomSheetModal>
    );
  },
);

type PeriodMarking = {
  color: string;
  textColor: string;
  startingDay?: boolean;
  endingDay?: boolean;
};

function buildMarkedDates(range: DateRange | null): Record<string, PeriodMarking> {
  if (!range) {
    return {};
  }

  const days = eachDayInRange(range);

  return days.reduce<Record<string, PeriodMarking>>((marked, day, index) => {
    marked[day] = {
      color: colors.orangeBg,
      textColor: colors.textPrimary,
      startingDay: index === 0,
      endingDay: index === days.length - 1,
    };

    return marked;
  }, {});
}

const calendarTheme = {
  arrowColor: colors.textPrimary,
  dayTextColor: colors.textPrimary,
  monthTextColor: colors.textPrimary,
  textDisabledColor: colors.border,
  textSectionTitleColor: colors.textSecondary,
  todayTextColor: colors.primary,
} as const;

const styles = StyleSheet.create({
  calendarWrapper: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    overflow: 'hidden',
  },
  footer: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: 'auto',
  },
  footerButton: {
    flex: 1,
  },
  sheet: {
    backgroundColor: colors.background,
    flex: 1,
    gap: spacing.md,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.body.fontSize,
    fontWeight: '700',
    textAlign: 'center',
  },
});
