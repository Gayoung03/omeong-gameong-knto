import type { ImageSourcePropType } from 'react-native';

/**
 * 혼디 캐릭터가 확정되면 mascot에 require('이미지 경로')를 지정합니다.
 * null인 동안에는 화면에 기본 플레이스홀더가 표시됩니다.
 */
export const chatbotAssets: {
  mascot: ImageSourcePropType | null;
} = {
  mascot: null,
};
