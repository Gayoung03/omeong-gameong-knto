import Ionicons from '@expo/vector-icons/Ionicons';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { colors } from '@/src/theme';

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];
const HOURS = Array.from({ length: 24 }, (_, index) => index);
const MINUTES = Array.from({ length: 12 }, (_, index) => index * 5);

/**
 * TODO(디자인 통일): 값은 theme 토큰을 가리키는 과도기 별칭이다. 추후 직접 참조로 정리할 것.
 */
const palette = {
  orange: colors.primary,
  ink: colors.textPrimary,
  gray: colors.textSecondary,
  line: colors.divider,
  paleOrange: colors.primarySoft,
  white: colors.surface,
};

const isSameDate = (left: Date, right: Date) =>
  left.getFullYear() === right.getFullYear() &&
  left.getMonth() === right.getMonth() &&
  left.getDate() === right.getDate();

export function CalendarPicker({ value, onChange }: { value: Date; onChange: (date: Date) => void }) {
  const [visibleMonth, setVisibleMonth] = useState(
    () => new Date(value.getFullYear(), value.getMonth(), 1),
  );

  const calendarCells = useMemo(() => {
    const year = visibleMonth.getFullYear();
    const month = visibleMonth.getMonth();
    const firstWeekday = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    return [
      ...Array.from({ length: firstWeekday }, () => null),
      ...Array.from({ length: daysInMonth }, (_, index) => new Date(year, month, index + 1)),
    ];
  }, [visibleMonth]);

  const moveMonth = (amount: number) => {
    setVisibleMonth(
      (month) => new Date(month.getFullYear(), month.getMonth() + amount, 1),
    );
  };

  return (
    <View style={styles.calendar}>
      <View style={styles.calendarHeader}>
        <Pressable accessibilityLabel="이전 달" onPress={() => moveMonth(-1)} style={styles.monthButton}>
          <Ionicons color={palette.ink} name="chevron-back" size={18} />
        </Pressable>
        <Text style={styles.monthTitle}>
          {visibleMonth.getFullYear()}년 {visibleMonth.getMonth() + 1}월
        </Text>
        <Pressable accessibilityLabel="다음 달" onPress={() => moveMonth(1)} style={styles.monthButton}>
          <Ionicons color={palette.ink} name="chevron-forward" size={18} />
        </Pressable>
      </View>

      <View style={styles.calendarGrid}>
        {WEEKDAYS.map((weekday, index) => (
          <View key={weekday} style={styles.calendarCell}>
            <Text
              style={[
                styles.weekdayText,
                index === 0 && styles.sundayText,
                index === 6 && styles.saturdayText,
              ]}
            >
              {weekday}
            </Text>
          </View>
        ))}
        {calendarCells.map((date, index) => {
          const selected = date ? isSameDate(date, value) : false;
          const past = date ? date < new Date(new Date().setHours(0, 0, 0, 0)) : false;
          return (
            <View key={date?.toISOString() ?? `empty-${index}`} style={styles.calendarCell}>
              {date ? (
                <Pressable
                  disabled={past}
                  onPress={() => {
                    const next = new Date(value);
                    next.setFullYear(date.getFullYear(), date.getMonth(), date.getDate());
                    onChange(next);
                  }}
                  style={[styles.dayButton, selected && styles.dayButtonSelected]}
                >
                  <Text
                    style={[
                      styles.dayText,
                      past && styles.pastDayText,
                      selected && styles.selectedDayText,
                    ]}
                  >
                    {date.getDate()}
                  </Text>
                </Pressable>
              ) : null}
            </View>
          );
        })}
      </View>
    </View>
  );
}

function WheelColumn({
  items,
  selected,
  suffix,
  onSelect,
}: {
  items: number[];
  selected: number;
  suffix: string;
  onSelect: (value: number) => void;
}) {
  const scrollRef = useRef<ScrollView>(null);
  const centeredValueRef = useRef(selected);
  const [centeredValue, setCenteredValue] = useState(selected);
  const selectedIndex = Math.max(items.indexOf(selected), 0);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ animated: false, y: selectedIndex * 42 });
    });

    return () => cancelAnimationFrame(frame);
    // The picker remounts whenever a different date/time field is opened.
    // Subsequent selected-value changes come from this wheel's own scroll position.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const scrollToIndex = (index: number, animated = true) => {
    const safeIndex = Math.max(0, Math.min(items.length - 1, index));
    scrollRef.current?.scrollTo({ animated, y: safeIndex * 42 });
  };

  const getIndexFromOffset = (offsetY: number) =>
    Math.max(0, Math.min(items.length - 1, Math.round(offsetY / 42)));

  const selectCenteredItem = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    const value = items[getIndexFromOffset(event.nativeEvent.contentOffset.y)];
    if (value === centeredValueRef.current) return;

    centeredValueRef.current = value;
    setCenteredValue(value);
    onSelect(value);
  };

  const snapAfterScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    scrollToIndex(getIndexFromOffset(event.nativeEvent.contentOffset.y));
  };

  return (
    <View style={styles.wheelColumn}>
      <View pointerEvents="none" style={styles.selectionBand} />
      <ScrollView
        contentContainerStyle={styles.wheelContent}
        decelerationRate="fast"
        onMomentumScrollEnd={snapAfterScroll}
        onScroll={selectCenteredItem}
        onScrollEndDrag={snapAfterScroll}
        ref={scrollRef}
        scrollEventThrottle={16}
        showsVerticalScrollIndicator={false}
        snapToInterval={42}
        style={styles.wheelScroll}
      >
        {items.map((item) => {
          const active = item === centeredValue;
          return (
            <Pressable
              key={item}
              onPress={() => scrollToIndex(items.indexOf(item))}
              style={styles.wheelItem}
            >
              <Text style={[styles.wheelText, active && styles.wheelTextSelected]}>
                {String(item).padStart(2, '0')}
                <Text style={styles.wheelSuffix}> {suffix}</Text>
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

export function WheelTimePicker({ value, onChange }: { value: Date; onChange: (date: Date) => void }) {
  const roundedMinute = Math.round(value.getMinutes() / 5) * 5 % 60;

  const changeTime = (hour: number, minute: number) => {
    const next = new Date(value);
    next.setHours(hour, minute, 0, 0);
    onChange(next);
  };

  return (
    <View style={styles.timePicker}>
      <View style={styles.timePreview}>
        <Ionicons color={palette.orange} name="time-outline" size={19} />
        <Text style={styles.timePreviewText}>
          {String(value.getHours()).padStart(2, '0')}:{String(roundedMinute).padStart(2, '0')}
        </Text>
      </View>
      <Text style={styles.wheelHint}>아래 목록을 스크롤하거나 시간을 눌러 선택하세요.</Text>
      <View style={styles.wheels}>
        <WheelColumn
          items={HOURS}
          onSelect={(hour) => changeTime(hour, roundedMinute)}
          selected={value.getHours()}
          suffix="시"
        />
        <Text style={styles.timeColon}>:</Text>
        <WheelColumn
          items={MINUTES}
          onSelect={(minute) => changeTime(value.getHours(), minute)}
          selected={roundedMinute}
          suffix="분"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  calendar: { paddingTop: 4 },
  calendarHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  monthButton: { alignItems: 'center', borderColor: palette.line, borderRadius: 9, borderWidth: 1, height: 34, justifyContent: 'center', width: 34 },
  monthTitle: { color: palette.ink, fontSize: 14, fontWeight: '900' },
  calendarGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  calendarCell: { alignItems: 'center', height: 38, justifyContent: 'center', width: '14.2857%' },
  weekdayText: { color: palette.gray, fontSize: 10, fontWeight: '800' },
  sundayText: { color: colors.calendarSunday },
  saturdayText: { color: colors.calendarSaturday },
  dayButton: { alignItems: 'center', borderRadius: 16, height: 32, justifyContent: 'center', width: 32 },
  dayButtonSelected: { backgroundColor: palette.orange },
  dayText: { color: palette.ink, fontSize: 11, fontWeight: '700' },
  pastDayText: { color: colors.textTertiary },
  selectedDayText: { color: palette.white, fontWeight: '900' },
  timePicker: { paddingTop: 2 },
  timePreview: { alignItems: 'center', alignSelf: 'center', backgroundColor: palette.paleOrange, borderRadius: 999, flexDirection: 'row', gap: 7, marginBottom: 7, paddingHorizontal: 15, paddingVertical: 8 },
  timePreviewText: { color: palette.orange, fontSize: 16, fontWeight: '900' },
  wheelHint: { color: palette.gray, fontSize: 9, marginBottom: 8, textAlign: 'center' },
  wheels: { alignItems: 'center', flexDirection: 'row', gap: 8, justifyContent: 'center' },
  wheelColumn: { borderColor: palette.line, borderRadius: 12, borderWidth: 1, height: 154, overflow: 'hidden', position: 'relative', width: 112 },
  wheelContent: { paddingVertical: 56 },
  selectionBand: { backgroundColor: palette.paleOrange, borderBottomColor: colors.primarySoftStrong, borderBottomWidth: 1, borderTopColor: colors.primarySoftStrong, borderTopWidth: 1, height: 42, left: 0, position: 'absolute', right: 0, top: 55 },
  wheelScroll: { zIndex: 1 },
  wheelItem: { alignItems: 'center', height: 42, justifyContent: 'center' },
  wheelText: { color: colors.textTertiary, fontSize: 13, fontWeight: '600' },
  wheelTextSelected: { color: palette.orange, fontSize: 17, fontWeight: '900' },
  wheelSuffix: { fontSize: 10, fontWeight: '700' },
  timeColon: { color: palette.ink, fontSize: 22, fontWeight: '900' },
});
