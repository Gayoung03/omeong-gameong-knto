import Ionicons from '@expo/vector-icons/Ionicons';
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { colors, radius, spacing, typography } from '@/src/theme';

import type { Trip } from '../types/trip';
import { DayChips } from './DayChips';
import { TripShareCard } from './TripShareCard';

type TripImagePreviewModalProps = {
  trip: Trip;
  /** wholeTrip 이면 전체 일정, day 면 고른 날짜 하나만 담는다 */
  mode: 'wholeTrip' | 'day';
  /** day 모드에서 처음 보여줄 날짜 */
  initialScheduleId: string;
  isSaving: boolean;
  onSave: (viewRef: React.RefObject<View | null>) => void;
  onShare: (viewRef: React.RefObject<View | null>) => void;
  onClose: () => void;
};

/**
 * 저장·공유하기 전에 만들어질 이미지를 먼저 보여준다.
 * 캡처 대상 뷰가 화면에 실제로 그려져 있어야 하므로,
 * 화면 밖에 숨겨두지 않고 미리보기로 띄운 뒤 캡처한다.
 */
export function TripImagePreviewModal({
  trip,
  mode,
  initialScheduleId,
  isSaving,
  onSave,
  onShare,
  onClose,
}: TripImagePreviewModalProps) {
  const cardRef = useRef<View>(null);
  const [selectedScheduleId, setSelectedScheduleId] = useState(initialScheduleId);

  const selectedSchedule =
    trip.schedules.find((schedule) => schedule.id === selectedScheduleId) ?? trip.schedules[0];

  const schedules = mode === 'wholeTrip' ? trip.schedules : [selectedSchedule];
  const title =
    mode === 'wholeTrip' ? '전체 일정 이미지' : `Day ${selectedSchedule.dayNumber} 이미지`;

  return (
    <Modal animationType="slide" onRequestClose={onClose} transparent visible>
      <View style={styles.backdrop}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>{title}</Text>
          <Pressable
            accessibilityLabel="닫기"
            accessibilityRole="button"
            hitSlop={spacing.sm}
            onPress={onClose}
          >
            <Ionicons color={colors.surface} name="close" size={24} />
          </Pressable>
        </View>

        {mode === 'day' && trip.schedules.length > 1 && (
          <View style={styles.daySelector}>
            <DayChips
              onSelectSchedule={setSelectedScheduleId}
              schedules={trip.schedules}
              selectedScheduleId={selectedSchedule.id}
            />
          </View>
        )}

        <ScrollView
          contentContainerStyle={styles.previewContent}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.cardWrapper}>
            <TripShareCard ref={cardRef} schedules={schedules} trip={trip} />
          </View>
        </ScrollView>

        <View style={styles.actions}>
          <Pressable
            accessibilityRole="button"
            disabled={isSaving}
            onPress={() => onShare(cardRef)}
            style={[styles.actionButton, styles.secondaryButton]}
          >
            <Ionicons color={colors.textPrimary} name="share-outline" size={17} />
            <Text style={styles.secondaryText}>공유</Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            disabled={isSaving}
            onPress={() => onSave(cardRef)}
            style={[styles.actionButton, styles.primaryButton, isSaving && styles.disabledButton]}
          >
            {isSaving ? (
              <ActivityIndicator color={colors.surface} size="small" />
            ) : (
              <>
                <Ionicons color={colors.surface} name="download-outline" size={17} />
                <Text style={styles.primaryText}>사진첩에 저장</Text>
              </>
            )}
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: 'rgba(30, 28, 25, 0.92)',
    flex: 1,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl + spacing.md,
    paddingBottom: spacing.sm,
  },
  headerTitle: {
    color: colors.surface,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  daySelector: {
    paddingBottom: spacing.xs,
  },
  previewContent: {
    alignItems: 'center',
    paddingBottom: spacing.lg,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
  },
  cardWrapper: {
    borderRadius: radius.lg,
    overflow: 'hidden',
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingBottom: spacing.xl + spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  actionButton: {
    alignItems: 'center',
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.xs + 2,
    justifyContent: 'center',
    paddingVertical: spacing.sm + 4,
  },
  secondaryButton: {
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.lg,
  },
  primaryButton: {
    backgroundColor: colors.primary,
    flex: 1,
  },
  disabledButton: {
    opacity: 0.7,
  },
  secondaryText: {
    color: colors.textPrimary,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
  primaryText: {
    color: colors.surface,
    fontSize: typography.label.fontSize,
    fontWeight: '700',
  },
});
