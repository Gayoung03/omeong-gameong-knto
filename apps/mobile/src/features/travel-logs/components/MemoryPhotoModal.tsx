import Ionicons from '@expo/vector-icons/Ionicons';
import { useCallback, useState } from 'react';
import { Modal, Pressable, Share, StyleSheet, Text, View } from 'react-native';
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import { colors, radius, spacing, typography } from '@/src/theme';
import type { TravelLog } from '@/src/types/travelLog';

import { useUpdatePersonalMessage } from '../hooks/useUpdatePersonalMessage';
import { MemoryCardBack } from './MemoryCardBack';
import { MemoryCardFront } from './MemoryCardFront';
import { PersonalMessageEditor } from './PersonalMessageEditor';

const FLIP_DURATION_MS = 500;

type MemoryPhotoModalProps = {
  tripId: string;
  log: TravelLog | undefined;
  onClose: () => void;
};

/** 여행 모아보기 화면 위에 뜨는 사진 팝업. 라우트 이동 없이 상태로만 앞/뒤를 전환한다. */
export function MemoryPhotoModal({ tripId, log, onClose }: MemoryPhotoModalProps) {
  const visible = log !== undefined;
  const rotation = useSharedValue(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const reducedMotion = useReducedMotion();
  const updateMessage = useUpdatePersonalMessage();
  // Modal이 fade-out되는 동안에도 내용이 사라지지 않도록 마지막 로그를 붙잡아둔다.
  const [displayLog, setDisplayLog] = useState(log);

  if (log && log !== displayLog) {
    setDisplayLog(log);
  }

  const resetModalState = useCallback(() => {
    setIsFlipped(false);
    setIsAnimating(false);
    setIsEditing(false);
    rotation.set(0);
  }, [rotation]);

  const handleClose = useCallback(() => {
    resetModalState();
    onClose();
  }, [onClose, resetModalState]);

  const handleFlip = useCallback(() => {
    if (isAnimating || isEditing) {
      return;
    }

    const nextFlipped = !isFlipped;
    setIsAnimating(true);
    setIsFlipped(nextFlipped);
    rotation.set(withTiming(
      nextFlipped ? 180 : 0,
      { duration: reducedMotion ? 0 : FLIP_DURATION_MS },
      (finished) => {
        if (finished) {
          runOnJS(setIsAnimating)(false);
        }
      },
    ));
  }, [isAnimating, isEditing, isFlipped, reducedMotion, rotation]);

  const frontStyle = useAnimatedStyle(() => ({
    transform: [{ perspective: 1200 }, { rotateY: `${rotation.value}deg` }],
  }));
  const backStyle = useAnimatedStyle(() => ({
    transform: [{ perspective: 1200 }, { rotateY: `${rotation.value - 180}deg` }],
  }));

  if (!displayLog) {
    return null;
  }

  const handleSaveMessage = (message: string | null) => {
    updateMessage.mutate(
      { tripId, logId: displayLog.logId, message },
      { onSuccess: () => setIsEditing(false) },
    );
  };

  const handleShare = () => {
    Share.share({
      message: displayLog.generatedImageUrl,
      title: '오멍가멍 여행 기록',
      url: displayLog.generatedImageUrl,
    }).catch(() => {
      // 공유 취소 등은 별도 안내 없이 무시한다.
    });
  };

  return (
    <Modal
      animationType="fade"
      onRequestClose={handleClose}
      onShow={resetModalState}
      statusBarTranslucent
      transparent
      visible={visible}
    >
      <Pressable
        accessibilityLabel="기록 닫기"
        accessibilityRole="button"
        onPress={handleClose}
        style={styles.overlay}
      >
        {/* 카드·버튼 영역을 별도 Pressable로 감싸 오버레이 닫기 탭이 전파되지 않게 한다 */}
        <Pressable onPress={() => {}} style={styles.content}>
          <View style={styles.flipContainer}>
            <Animated.View
              accessibilityLabel="기록 앞면"
              style={[styles.face, frontStyle]}
              pointerEvents={isFlipped ? 'none' : 'auto'}
            >
              <Pressable
                accessibilityLabel="기록 뒷면 보기"
                accessibilityRole="button"
                disabled={isAnimating}
                onPress={handleFlip}
                style={styles.faceCard}
              >
                <MemoryCardFront log={displayLog} />
              </Pressable>
            </Animated.View>

            <Animated.View
              accessibilityLabel="기록 뒷면"
              style={[styles.face, styles.faceBack, backStyle]}
              pointerEvents={isFlipped ? 'auto' : 'none'}
            >
              <Pressable
                accessibilityLabel="기록 앞면 보기"
                accessibilityRole="button"
                disabled={isAnimating || isEditing}
                onPress={handleFlip}
                style={styles.faceCard}
              >
                {isEditing ? (
                  <PersonalMessageEditor
                    initialValue={displayLog.personalMessage ?? ''}
                    isSaving={updateMessage.isPending}
                    onCancel={() => setIsEditing(false)}
                    onSave={handleSaveMessage}
                  />
                ) : (
                  <MemoryCardBack log={displayLog} onEditPress={() => setIsEditing(true)} />
                )}
              </Pressable>
            </Animated.View>
          </View>

          <IconCloseButton onPress={handleClose} />

          <Text style={styles.hint}>
            {isFlipped ? '카드를 눌러 사진으로 돌아가기' : '사진을 눌러 뒷면의 기록을 확인해 보세요'}
          </Text>

          <View style={styles.actions}>
            <Pressable accessibilityRole="button" onPress={handleShare} style={styles.shareButton}>
              <Ionicons color={colors.secondary} name="share-social-outline" size={16} />
              <Text style={styles.shareLabel}>공유하기</Text>
            </Pressable>
            {/* TODO: 사진 저장 — expo-media-library 등 미디어 저장 패키지 도입 후 연결 */}
            <Pressable accessibilityRole="button" style={styles.saveButton}>
              <Ionicons color={colors.surface} name="download-outline" size={16} />
              <Text style={styles.saveLabel}>사진 저장</Text>
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function IconCloseButton({ onPress }: { onPress: () => void }) {
  return (
    <Pressable
      accessibilityLabel="기록 닫기"
      accessibilityRole="button"
      hitSlop={spacing.sm}
      onPress={onPress}
      style={styles.closeButton}
    >
      <Ionicons color={colors.textPrimary} name="close" size={18} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.md,
    width: '100%',
  },
  closeButton: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 9999,
    height: 32,
    justifyContent: 'center',
    position: 'absolute',
    right: -spacing.xs,
    top: -spacing.md,
    width: 32,
  },
  content: {
    alignItems: 'center',
    marginHorizontal: 20,
    maxHeight: '90%',
    width: '100%',
  },
  face: {
    backfaceVisibility: 'hidden',
    borderRadius: radius.lg,
    bottom: 0,
    left: 0,
    overflow: 'hidden',
    position: 'absolute',
    right: 0,
    top: 0,
  },
  faceBack: {
    backgroundColor: colors.surface,
  },
  faceCard: {
    flex: 1,
  },
  flipContainer: {
    aspectRatio: 0.74,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    width: '100%',
  },
  hint: {
    color: 'rgba(255,255,255,0.85)',
    fontSize: typography.body.fontSize - 3,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  overlay: {
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.6)',
    flex: 1,
    justifyContent: 'center',
  },
  saveButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    flex: 1,
    flexDirection: 'row',
    gap: spacing.xs,
    justifyContent: 'center',
    paddingVertical: spacing.sm + 2,
  },
  saveLabel: {
    color: colors.surface,
    fontSize: typography.body.fontSize - 2,
    fontWeight: '700',
  },
  shareButton: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderColor: colors.secondary,
    borderRadius: radius.md,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    gap: spacing.xs,
    justifyContent: 'center',
    paddingVertical: spacing.sm + 2,
  },
  shareLabel: {
    color: colors.secondary,
    fontSize: typography.body.fontSize - 2,
    fontWeight: '700',
  },
});
