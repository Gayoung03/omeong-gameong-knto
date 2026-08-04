import type { ImageSourcePropType } from 'react-native';

/**
 * 로고와 캐릭터를 교체할 때 이 파일의 source만 변경하면 됩니다.
 * logo가 null이면 텍스트형 기본 로고를 사용합니다.
 */
export const authBrandAssets: {
  logo: ImageSourcePropType | null;
  mascot: ImageSourcePropType;
} = {
  logo: null,
  mascot: require('../../../../assets/illustrations/auth/auth-mascot.png'),
};

