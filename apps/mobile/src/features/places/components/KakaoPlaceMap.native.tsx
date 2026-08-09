import { StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';

import type { KakaoPlaceMapProps } from './KakaoPlaceMap.types';
import { buildKakaoMapDocument } from './buildKakaoMapDocument';

export function KakaoPlaceMap({ appKey, places }: KakaoPlaceMapProps) {
  return (
    <WebView
      bounces={false}
      javaScriptEnabled
      originWhitelist={['https://*']}
      showsHorizontalScrollIndicator={false}
      showsVerticalScrollIndicator={false}
      source={{
        baseUrl: 'https://localhost',
        html: buildKakaoMapDocument(appKey, places),
      }}
      style={styles.map}
    />
  );
}

const styles = StyleSheet.create({
  map: {
    flex: 1,
    backgroundColor: '#EEF8F7',
  },
});
