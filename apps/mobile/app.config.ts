import type { ExpoConfig } from 'expo/config';

const config: ExpoConfig = {
  name: '오멍가멍',
  slug: 'omeong-gameong',
  version: '0.1.0',
  orientation: 'portrait',
  scheme: 'omeonggameong',
  userInterfaceStyle: 'automatic',
  ios: {
    supportsTablet: true,
    bundleIdentifier: 'com.omeonggameong.app',
  },
  android: {
    package: 'com.omeonggameong.app',
    predictiveBackGestureEnabled: false,
  },
  web: {
    output: 'static',
  },
  plugins: [
    'expo-router',
    'expo-secure-store',
    '@react-native-community/datetimepicker',
    'expo-sharing',
    [
      'expo-media-library',
      {
        photosPermission: '여행 일정을 이미지로 저장하기 위해 사진 접근 권한이 필요해요.',
        savePhotosPermission: '만든 여행 일정 이미지를 사진첩에 저장할게요.',
        isAccessMediaLocationEnabled: false,
      },
    ],
  ],
  experiments: {
    typedRoutes: true,
  },
};

export default config;
