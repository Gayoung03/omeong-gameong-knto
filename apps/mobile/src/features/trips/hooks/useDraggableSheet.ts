import { useMemo } from 'react';
import { Gesture } from 'react-native-gesture-handler';
import { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';

type UseDraggableSheetParams = {
  /** 아래에서부터의 높이 후보(px). 오름차순으로 넣는다 */
  snapPoints: number[];
  /** 처음 보여줄 높이의 인덱스 */
  initialIndex: number;
  /** 시트 위에 띄울 요소를 시트에서 얼마나 띄울지 */
  aboveSheetGap?: number;
};

const SPRING_CONFIG = { damping: 22, stiffness: 220 };

/** 손을 떼는 순간의 속도를 반영해 도착할 지점을 예측한다 */
const VELOCITY_FACTOR = 0.12;

/**
 * 아래에서 끌어올려 크기를 조절하는 바텀시트.
 *
 * 제스처는 시트 전체가 아니라 손잡이 영역에만 붙인다.
 * 목록(FlatList)과 지도(WebView) 위에 붙이면 스크롤·지도 조작과 서로 먹히기 때문이다.
 *
 * 제스처 객체를 `useMemo` 로 감싸지 않는 이유
 * -----------------------------------------
 * shared value 를 의존성 배열에 넣으면 `react-hooks/immutability` 규칙이
 * "hook 에 넘긴 값은 수정할 수 없다"며 `height.value = ...` 를 막는다.
 * 제스처는 렌더마다 새로 만들어도 GestureDetector 가 알아서 갱신한다.
 */
export function useDraggableSheet({
  snapPoints,
  initialIndex,
  aboveSheetGap = 16,
}: UseDraggableSheetParams) {
  const points = useMemo(() => [...snapPoints].sort((a, b) => a - b), [snapPoints]);
  const minHeight = points[0] ?? 0;
  const maxHeight = points[points.length - 1] ?? 0;
  const initialHeight = points[initialIndex] ?? minHeight;

  const height = useSharedValue(initialHeight);
  const startHeight = useSharedValue(initialHeight);

  const gesture = Gesture.Pan()
    .onStart(() => {
      startHeight.value = height.value;
    })
    .onUpdate((event) => {
      // 위로 끌면 translationY 가 음수라 높이가 커진다
      const next = startHeight.value - event.translationY;
      height.value = Math.min(Math.max(next, minHeight), maxHeight);
    })
    .onEnd((event) => {
      const projected = height.value - event.velocityY * VELOCITY_FACTOR;

      let target = minHeight;
      let shortestDistance = Number.POSITIVE_INFINITY;

      for (let index = 0; index < points.length; index += 1) {
        const distance = Math.abs(points[index] - projected);

        if (distance < shortestDistance) {
          shortestDistance = distance;
          target = points[index];
        }
      }

      height.value = withSpring(target, SPRING_CONFIG);
    });

  const sheetStyle = useAnimatedStyle(() => ({ height: height.value }));

  /** 시트 바로 위에 붙여 두고 싶은 요소(지도 버튼 등)에 쓴다 */
  const aboveSheetStyle = useAnimatedStyle(() => ({ bottom: height.value + aboveSheetGap }));

  return { gesture, sheetStyle, aboveSheetStyle };
}
