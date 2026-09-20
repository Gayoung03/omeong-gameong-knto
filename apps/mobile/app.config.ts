import type { ExpoConfig } from 'expo/config';

const config: ExpoConfig = {
  name: '오멍가멍',
  slug: 'omeong-gameong',
  version: '0.1.0',
  orientation: 'portrait',
  scheme: 'omeonggameong',
  // 런처 아이콘(1024×1024, 알파 없음). 원본 0830 아이콘을 배경색으로 평면화한 것.
  icon: './assets/icons/app-icon.png',
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
    // 적응형 아이콘: 런처 마스크(원·둥근사각)가 가장자리를 잘라내므로 전경은 안전 영역
    // 안에 들어가게 72% 로 줄인 투명 캔버스본을 쓰고 배경은 아이콘 크림색으로 채운다.
    adaptiveIcon: {
      foregroundImage: './assets/icons/adaptive-icon-foreground.png',
      backgroundColor: '#FBF3EB',
    },
    // Play 사진·동영상 권한 정책: 넓은 미디어 읽기 권한은 신고·승인 대상이다.
    // 사진 선택은 시스템 사진 선택기(expo-image-picker), 저장은 write-only 라 필요 없다.
    blockedPermissions: [
      'android.permission.READ_MEDIA_IMAGES',
      'android.permission.READ_MEDIA_VIDEO',
      'android.permission.READ_MEDIA_AUDIO',
    ],
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
        // 갤러리 저장(write-only)만 쓰므로 세분 읽기 권한을 요청하지 않는다.
        granularPermissions: [],
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
