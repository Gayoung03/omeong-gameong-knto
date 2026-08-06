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
    [
      'expo-image-picker',
      {
        cameraPermission: '여행의 순간을 촬영하려면 카메라 접근이 필요합니다.',
        microphonePermission: false,
        photosPermission: '여행 사진을 선택하려면 사진 앨범 접근이 필요합니다.',
      },
    ],
  ],
  experiments: {
    typedRoutes: true,
  },
};

export default config;
