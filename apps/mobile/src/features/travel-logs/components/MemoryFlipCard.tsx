import { useCallback, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';

import { colors, radius } from '@/src/theme';
import type { TravelLog } from '@/src/types/travelLog';

import { MemoryCardBack } from './MemoryCardBack';
import { MemoryCardFront } from './MemoryCardFront';

const FLIP_DURATION_MS = 500;

type MemoryFlipCardProps = {
  log: TravelLog;
  /** 뒷면의 한 줄 기록 수정 진입. 없으면 수정 버튼이 나오지 않는다. */
  onEditPress?: () => void;
  onFlipChange?: (isFlipped: boolean) => void;
  /** 카드 세로 비율. 팝업보다 여백이 적은 화면에서는 더 정사각형에 가깝게 쓴다. */
  aspectRatio?: number;
};

/**
 * 화면 안에 그대로 놓고 쓰는 앞/뒤 뒤집기 카드.
 * 팝업(MemoryPhotoModal)과 같은 회전 방식이지만, 모달·공유 버튼 없이 카드만 담당한다.
 */
export function MemoryFlipCard({
  log,
  onEditPress,
  onFlipChange,
  aspectRatio = 0.74,
}: MemoryFlipCardProps) {
  const rotation = useSharedValue(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const reducedMotion = useReducedMotion();

  const handleFlip = useCallback(() => {
    if (isAnimating) return;

    const nextFlipped = !isFlipped;
    setIsAnimating(true);
    setIsFlipped(nextFlipped);
    onFlipChange?.(nextFlipped);
    rotation.set(
      withTiming(
        nextFlipped ? 180 : 0,
        { duration: reducedMotion ? 0 : FLIP_DURATION_MS },
        (finished) => {
          if (finished) {
            runOnJS(setIsAnimating)(false);
          }
        },
      ),
    );
  }, [isAnimating, isFlipped, onFlipChange, reducedMotion, rotation]);

  const frontStyle = useAnimatedStyle(() => ({
    transform: [{ perspective: 1200 }, { rotateY: `${rotation.value}deg` }],
  }));
  const backStyle = useAnimatedStyle(() => ({
    transform: [{ perspective: 1200 }, { rotateY: `${rotation.value - 180}deg` }],
  }));

  return (
    <View style={[styles.flipContainer, { aspectRatio }]}>
      <Animated.View
        accessibilityLabel="기록 앞면"
        pointerEvents={isFlipped ? 'none' : 'auto'}
        style={[styles.face, frontStyle]}
      >
        <Pressable
          accessibilityLabel="기록 뒷면 보기"
          accessibilityRole="button"
          disabled={isAnimating}
          onPress={handleFlip}
          style={styles.faceCard}
        >
          <MemoryCardFront log={log} />
        </Pressable>
      </Animated.View>

      <Animated.View
        accessibilityLabel="기록 뒷면"
        pointerEvents={isFlipped ? 'auto' : 'none'}
        style={[styles.face, styles.faceBack, backStyle]}
      >
        <Pressable
          accessibilityLabel="기록 앞면 보기"
          accessibilityRole="button"
          disabled={isAnimating}
          onPress={handleFlip}
          style={styles.faceCard}
        >
          <MemoryCardBack log={log} onEditPress={onEditPress} />
        </Pressable>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
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
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    width: '100%',
  },
});
