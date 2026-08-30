import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

import type { AddScheduleInput, PlaceCandidate, Schedule } from '../types/trip';
import { toSchedulePlace } from '../utils/placeCandidate';
import { formatPlaceMeta } from '../utils/tripFormat';
import { DayChips } from './DayChips';
import { PetPolicyBadge } from './PetPolicyBadge';
import { TimeField } from './TimeField';

type AddScheduleSheetProps = {
  place: PlaceCandidate;
  schedules: Schedule[];
  /** 처음 선택되어 있을 날짜 */
  initialScheduleId: string;
  onSubmit: (input: AddScheduleInput) => void;
  onClose: () => void;
};

const MEMO_MAX_LENGTH = 100;

/**
 * 장소를 고른 뒤 날짜·시간·메모를 정해 일정에 담는 바텀시트.
 *
 * 장소를 고른 뒤에만 마운트한다. 초기값을 useState 로 한 번만 읽기 때문에
 * effect 안에서 상태를 다시 맞출 필요가 없다.
 */
export function AddScheduleSheet({
  place,
  schedules,
  initialScheduleId,
  onSubmit,
  onClose,
}: AddScheduleSheetProps) {
  const [scheduleId, setScheduleId] = useState(initialScheduleId || (schedules[0]?.id ?? ''));
  const [startTime, setStartTime] = useState<string | null>(null);
  const [memo, setMemo] = useState('');

  const handleSubmit = () => {
    onSubmit({ scheduleId, place: toSchedulePlace(place), startTime, memo: memo.trim() });
  };

  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible>
      <View style={styles.backdrop}>
        <Pressable
          accessibilityLabel="닫기"
          accessibilityRole="button"
          onPress={onClose}
          style={styles.backdropArea}
        />

        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <View style={styles.sheet}>
            <View style={styles.grip} />

            <View style={styles.header}>
              <View style={styles.headerTexts}>
                <Text numberOfLines={1} style={styles.placeName}>
                  {place.name}
                </Text>
                <Text style={styles.placeMeta}>
                  {formatPlaceMeta(place.category, place.regionLabel)}
                </Text>
              </View>
              <Pressable
                accessibilityLabel="닫기"
                accessibilityRole="button"
                hitSlop={spacing.sm}
                onPress={onClose}
              >
                <Ionicons color={colors.textSecondary} name="close" size={22} />
              </Pressable>
            </View>

            <PetPolicyBadge petPolicy={place.petPolicy} />

            <ScrollView
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
              style={styles.form}
            >
              <Text style={styles.sectionLabel}>어느 날에 담을까요?</Text>
              <DayChips
                onSelectSchedule={setScheduleId}
                schedules={schedules}
                selectedScheduleId={scheduleId}
              />

              <Text style={styles.sectionLabel}>방문 기준 시각 · 선택</Text>
              <TimeField onChangeValue={setStartTime} value={startTime} />
              <Text style={styles.timeHint}>비워두면 현재 순서를 기준으로 시간을 계산해요.</Text>

              <Text style={styles.sectionLabel}>메모</Text>
              <TextInput
                maxLength={MEMO_MAX_LENGTH}
                multiline
                onChangeText={setMemo}
                placeholder="예: 테라스 좌석만 반려견 동반 가능"
                placeholderTextColor={colors.textTertiary}
                style={styles.memoInput}
                value={memo}
              />
              <Text style={styles.memoCount}>
                {memo.length} / {MEMO_MAX_LENGTH}
              </Text>
            </ScrollView>

            <Pressable
              accessibilityRole="button"
              disabled={scheduleId.length === 0}
              onPress={handleSubmit}
              style={[styles.submitButton, scheduleId.length === 0 && styles.disabledButton]}
            >
              <Text style={styles.submitText}>일정에 담기</Text>
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: overlayColors.scrim,
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdropArea: {
    flex: 1,
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl + 4,
    borderTopRightRadius: radius.xl + 4,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  grip: {
    alignSelf: 'center',
    backgroundColor: colors.border,
    borderRadius: radius.sm,
    height: 4,
    marginBottom: spacing.md,
    width: 40,
  },
  header: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  headerTexts: {
    flex: 1,
  },
  placeName: {
    color: colors.basalt,
    fontSize: typography.sectionTitle.fontSize,
    fontWeight: typography.sectionTitle.fontWeight,
  },
  placeMeta: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    marginTop: 2,
  },
  form: {
    maxHeight: 340,
  },
  sectionLabel: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
    marginTop: spacing.md,
  },
  memoInput: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.basalt,
    fontSize: typography.caption.fontSize + 1,
    marginTop: spacing.sm,
    minHeight: 68,
    paddingHorizontal: spacing.sm + 4,
    paddingVertical: spacing.sm + 2,
    textAlignVertical: 'top',
  },
  memoCount: {
    alignSelf: 'flex-end',
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    marginTop: spacing.xs,
  },
  submitButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    marginTop: spacing.md,
    paddingVertical: spacing.md - 2,
  },
  disabledButton: {
    backgroundColor: colors.border,
  },
  submitText: {
    color: colors.surface,
    fontSize: typography.label.fontSize + 2,
    fontWeight: '700',
  },
  timeHint: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    marginTop: spacing.xs,
  },
});
