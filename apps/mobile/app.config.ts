import type { ExpoConfig } from 'expo/config';

const config: ExpoConfig = {
  name: '오멍가멍',
  slug: 'omeong-gameong',
  version: '0.1.0',
  orientation: 'portrait',
  scheme: 'omeonggameong',
  extra: {
    eas: {
      projectId: process.env.EXPO_PUBLIC_EAS_PROJECT_ID,
    },
  },
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
    // 'static'은 모든 라우트를 Node에서 프리렌더한다.
    // 네이티브 전제 모듈(webview·view-shot 등)이 Node 환경에서 깨지므로
    // 클라이언트 렌더링(SPA)인 'single'을 사용한다.
    output: 'single',
  },
  plugins: [
    'expo-router',
    'expo-notifications',
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
