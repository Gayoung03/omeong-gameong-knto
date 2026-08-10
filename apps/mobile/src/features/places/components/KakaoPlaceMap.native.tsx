import { StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';

import type { KakaoPlaceMapProps } from './KakaoPlaceMap.types';
import { buildKakaoMapDocument } from './buildKakaoMapDocument';

import { colors } from '@/src/theme';

export function KakaoPlaceMap({ appKey, places }: KakaoPlaceMapProps) {
  return (
    <WebView
      bounces={false}
      javaScriptEnabled
      originWhitelist={['*']}
      showsHorizontalScrollIndicator={false}
      showsVerticalScrollIndicator={false}
      // baseUrl 을 지정하지 않는다. 지정하면 그 주소가 출처(Referer)로 카카오에 전달되는데,
      // 카카오 콘솔은 localhost 를 사이트 도메인으로 받아주지 않아 SDK 로드가 거부된다.
      // 출처를 아예 보내지 않으면 카카오가 허용하므로 개발 중에는 이 상태로 둔다.
      // 배포 도메인이 정해지면 trips 의 KAKAO_MAP_BASE_URL 과 같은 값을 여기에도 넣는다.
      source={{
        html: buildKakaoMapDocument(appKey, places),
      }}
      style={styles.map}
    />
  );
}

const styles = StyleSheet.create({
  map: {
    flex: 1,
    backgroundColor: colors.seaSoftLight,
  },
});
