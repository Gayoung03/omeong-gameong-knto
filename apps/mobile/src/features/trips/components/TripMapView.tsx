import Ionicons from '@expo/vector-icons/Ionicons';
import { forwardRef, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';

import { colors, radius, spacing, typography } from '@/src/theme';

import { KAKAO_JS_KEY, KAKAO_MAP_BASE_URL } from '../constants/map';
import type { PlaceCandidate, ScheduleItem } from '../types/trip';
import {
  buildKakaoMapHtml,
  type KakaoMapFitMode,
  type KakaoMapMessage,
} from '../utils/kakaoMapHtml';

/**
 * 지도를 다시 그리지 않고 보여줄 범위만 바꾸는 통로.
 * 버튼은 화면마다 위치가 달라서 여기서 그리지 않고 밖에 맡긴다.
 */
export type TripMapViewHandle = {
  fitTo: (mode: KakaoMapFitMode) => void;
};

type TripMapViewProps = {
  items: ScheduleItem[];
  /**
   * 이 값이 바뀌면 지도를 새로 그린다.
   * 마커 선택처럼 자주 바뀌는 값을 넣으면 화면이 튀므로 넣지 않는다.
   */
  redrawKey: string;
  /** 지도를 그릴 때 강조해둘 장소 */
  initialSelectedPlaceId: string | null;
  onSelectPlace: (placeId: string | null) => void;
  /** 아직 일정에 담기지 않은 후보 장소 */
  candidates?: PlaceCandidate[];
  initialFitMode?: KakaoMapFitMode;
};

const MAP_COLORS = {
  marker: colors.primary,
  markerText: colors.surface,
  selectedMarker: colors.leaf,
  routeLine: colors.sea,
  background: colors.background,
  candidateMarker: colors.leaf,
};

export const TripMapView = forwardRef<TripMapViewHandle, TripMapViewProps>(function TripMapView(
  { items, redrawKey, initialSelectedPlaceId, onSelectPlace, candidates, initialFitMode = 'route' },
  ref,
) {
  const webViewRef = useRef<WebView>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  /** 지도를 다시 그리지 않고 범위만 옮긴다 */
  useImperativeHandle(ref, () => ({
    fitTo: (mode: KakaoMapFitMode) => {
      webViewRef.current?.injectJavaScript(
        `if (window.fitTo) { window.fitTo(${JSON.stringify(mode)}); } true;`,
      );
    },
  }));

  const html = useMemo(
    () =>
      buildKakaoMapHtml({
        items,
        candidates,
        initialSelectedPlaceId,
        initialFitMode,
        colors: MAP_COLORS,
      }),
    [items, candidates, initialSelectedPlaceId, initialFitMode],
  );

  // 기준 주소를 비워두면 카카오에 출처를 보내지 않는다 (constants/map.ts 참고)
  const source = KAKAO_MAP_BASE_URL ? { html, baseUrl: KAKAO_MAP_BASE_URL } : { html };

  const handleMessage = (event: WebViewMessageEvent) => {
    let message: KakaoMapMessage;

    try {
      message = JSON.parse(event.nativeEvent.data) as KakaoMapMessage;
    } catch {
      return;
    }

    if (message.type === 'markerPress') {
      onSelectPlace(message.placeId);
      return;
    }
    if (message.type === 'mapPress') {
      onSelectPlace(null);
      return;
    }
    if (message.type === 'ready') {
      setIsLoading(false);
      return;
    }
    if (message.type === 'error') {
      setIsLoading(false);
      setErrorMessage(message.message);
    }
  };

  if (KAKAO_JS_KEY.length === 0) {
    return (
      <MapNotice
        description={'.env 에 EXPO_PUBLIC_KAKAO_JS_KEY 를 넣고 앱을 다시 실행하면 지도가 표시돼요.'}
        iconName="key-outline"
        title="카카오 지도 키가 없어요"
      />
    );
  }

  if (errorMessage) {
    return (
      <MapNotice
        description={errorMessage}
        iconName="alert-circle-outline"
        title="지도를 불러오지 못했어요"
      />
    );
  }

  return (
    <View style={styles.container}>
      <WebView
        allowsInlineMediaPlayback
        // iOS 에서 로컬 HTML 이 외부 스크립트를 불러올 수 있게 한다
        allowFileAccessFromFileURLs
        allowUniversalAccessFromFileURLs
        // 안드로이드에서 http 기준 페이지가 https 스크립트를 불러올 수 있게 한다
        mixedContentMode="always"
        // 이 값이 바뀔 때만 지도를 새로 그린다. 마커 선택은 WebView 안에서 처리한다
        key={redrawKey}
        onError={(event) =>
          setErrorMessage(`WebView 오류: ${event.nativeEvent.description ?? '알 수 없음'}`)
        }
        onHttpError={(event) =>
          setErrorMessage(
            `HTTP ${event.nativeEvent.statusCode} — ${event.nativeEvent.url ?? '알 수 없는 주소'}`,
          )
        }
        onMessage={handleMessage}
        originWhitelist={['*']}
        ref={webViewRef}
        source={source}
        style={styles.webView}
      />

      {isLoading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator color={colors.primary} />
        </View>
      )}
    </View>
  );
});

type MapNoticeProps = {
  iconName: keyof typeof Ionicons.glyphMap;
  title: string;
  description: string;
};

function MapNotice({ iconName, title, description }: MapNoticeProps) {
  return (
    <View style={styles.notice}>
      <Ionicons color={colors.textTertiary} name={iconName} size={30} />
      <Text style={styles.noticeTitle}>{title}</Text>
      <Text style={styles.noticeDescription}>{description}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    overflow: 'hidden',
  },
  webView: {
    backgroundColor: colors.background,
    flex: 1,
  },
  loadingOverlay: {
    alignItems: 'center',
    backgroundColor: colors.background,
    bottom: 0,
    justifyContent: 'center',
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  notice: {
    alignItems: 'center',
    backgroundColor: colors.basaltSoft,
    borderRadius: radius.lg,
    flex: 1,
    gap: spacing.sm,
    justifyContent: 'center',
    margin: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  noticeTitle: {
    color: colors.textPrimary,
    fontSize: typography.subtitle.fontSize,
    fontWeight: typography.subtitle.fontWeight,
  },
  noticeDescription: {
    color: colors.textSecondary,
    fontSize: typography.caption.fontSize,
    lineHeight: 18,
    textAlign: 'center',
  },
});
