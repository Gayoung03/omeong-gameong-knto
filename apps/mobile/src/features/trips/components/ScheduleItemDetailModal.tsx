import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { colors, overlayColors, radius, spacing, typography } from '@/src/theme';

import { TimeField } from './TimeField';
import type { ScheduleItem } from '../types/trip';

const MEMO_MAX_LENGTH = 100;

type ScheduleItemDetailModalProps = {
  item: ScheduleItem;
  onSubmit: (patch: { startTime: string | null; memo: string }) => void;
  onClose: () => void;
};

/**
 * 일정의 방문 시각·메모를 고치는 시트.
 *
 * **여기서 고칠 수 있는 것은 이 둘뿐이다.** 서버 `PATCH /route-items` 가 받는 것도
 * 시각·체류시간·메모이고, 순서와 날짜는 각각 순서 API·삭제 후 재생성으로 처리한다
 * (`api/scheduleSync.ts`).
 *
 * 항목을 고른 뒤에만 마운트한다. 초기값을 `useState` 로 한 번만 읽기 때문에
 * effect 안에서 상태를 다시 맞출 필요가 없다.
 */
export function ScheduleItemDetailModal({ item, onSubmit, onClose }: ScheduleItemDetailModalProps) {
  const [startTime, setStartTime] = useState<string | null>(item.startTime);
  const [memo, setMemo] = useState(item.memo);

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
              <Text numberOfLines={1} style={styles.placeName}>
                {item.place.name}
              </Text>
              <Pressable
                accessibilityLabel="닫기"
                accessibilityRole="button"
                hitSlop={spacing.sm}
                onPress={onClose}
              >
                <Ionicons color={colors.textSecondary} name="close" size={22} />
              </Pressable>
            </View>

            <Text style={styles.sectionLabel}>방문 기준 시각</Text>
            <TimeField onChangeValue={setStartTime} value={startTime} />
            <Text style={styles.timeHint}>이 시각을 기준으로 뒤 일정 시간이 조정돼요.</Text>

            <Text style={styles.sectionLabel}>메모</Text>
            <TextInput
              maxLength={MEMO_MAX_LENGTH}
              multiline
              onChangeText={setMemo}
              placeholder="예: 테라스 좌석만 반려견 동반 가능"
              placeholderTextColor={colors.textTertiary}
              style={styles.memoInput}
              textAlignVertical="top"
              value={memo}
            />
            <Text style={styles.memoCount}>
              {memo.length} / {MEMO_MAX_LENGTH}
            </Text>

            <Pressable
              accessibilityRole="button"
              onPress={() => onSubmit({ memo: memo.trim(), startTime })}
              style={styles.submitButton}
            >
              <Text style={styles.submitText}>확인</Text>
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
  grip: {
    alignSelf: 'center',
    backgroundColor: colors.border,
    borderRadius: radius.sm,
    height: 4,
    marginBottom: spacing.md,
    width: 40,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
  },
  memoCount: {
    alignSelf: 'flex-end',
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    marginTop: spacing.xs,
  },
  memoInput: {
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.textPrimary,
    fontSize: typography.label.fontSize + 1,
    minHeight: 78,
    padding: spacing.sm + 2,
  },
  placeName: {
    color: colors.basalt,
    flex: 1,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  sectionLabel: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    fontWeight: typography.micro.fontWeight,
    marginBottom: spacing.xs + 2,
    marginTop: spacing.md,
  },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.xl + 4,
    borderTopRightRadius: radius.xl + 4,
    paddingBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  submitButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    marginTop: spacing.md,
    paddingVertical: spacing.sm + 4,
  },
  timeHint: {
    color: colors.textTertiary,
    fontSize: typography.micro.fontSize,
    marginTop: spacing.xs,
  },
  submitText: {
    color: colors.surface,
    fontSize: typography.label.fontSize + 1,
    fontWeight: '700',
  },
});
