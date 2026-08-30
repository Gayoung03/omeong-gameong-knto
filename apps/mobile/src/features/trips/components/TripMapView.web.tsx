import Ionicons from '@expo/vector-icons/Ionicons';
import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { HtmlFrame } from '@/src/components/web/HtmlFrame.web';
import { colors, radius, spacing, typography } from '@/src/theme';

import { KAKAO_JS_KEY } from '../constants/map';
import type { PlaceCandidate, ScheduleItem } from '../types/trip';
import {
  buildKakaoMapHtml,
  type KakaoMapFitMode,
  type KakaoMapMessage,
} from '../utils/kakaoMapHtml';

export type TripMapViewHandle = {
  fitTo: (mode: KakaoMapFitMode) => void;
};

type Props = {
  items: ScheduleItem[];
  redrawKey: string;
  initialSelectedPlaceId: string | null;
  onSelectPlace: (placeId: string | null) => void;
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

/**
 * react-native-webview 가 웹을 지원하지 않아 iframe 으로 지도를 띄운다.
 * 프레임 방식은 HtmlFrame 주석 참고 (srcDoc 을 쓰면 HTTPS 배포에서 지도가 차단된다).
 */
export const TripMapView = forwardRef<TripMapViewHandle, Props>(function TripMapView(
  { items, redrawKey, initialSelectedPlaceId, onSelectPlace, candidates, initialFitMode = 'route' },
  ref,
) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
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

  useImperativeHandle(ref, () => ({
    fitTo: (mode) => iframeRef.current?.contentWindow?.postMessage({ type: 'fitTo', mode }, '*'),
  }));

  useEffect(() => {
    const receiveMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow || typeof event.data !== 'string')
        return;
      let message: KakaoMapMessage;
      try {
        message = JSON.parse(event.data) as KakaoMapMessage;
      } catch {
        return;
      }
      if (message.type === 'markerPress') onSelectPlace(message.placeId);
      if (message.type === 'mapPress') onSelectPlace(null);
      if (message.type === 'ready') {
        setIsLoading(false);
      }
      if (message.type === 'error') {
        setIsLoading(false);
        setErrorMessage(message.message);
      }
    };

    window.addEventListener('message', receiveMessage);
    return () => {
      window.removeEventListener('message', receiveMessage);
    };
  }, [html, redrawKey, onSelectPlace]);

  if (!KAKAO_JS_KEY) {
    return (
      <MapNotice description="카카오 JavaScript 키를 설정해주세요." title="지도 연결이 필요해요" />
    );
  }
  if (errorMessage) {
    return <MapNotice description={errorMessage} title="지도를 불러오지 못했어요" />;
  }

  return (
    <View style={styles.container}>
      <HtmlFrame
        backgroundColor={colors.background}
        html={html}
        key={redrawKey}
        onFrame={(frame) => {
          iframeRef.current = frame;
        }}
        onWrite={() => {
          setIsLoading(false);
          setErrorMessage(null);
        }}
        title="여행 경로 지도"
      />
      {isLoading ? (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : null}
    </View>
  );
});

function MapNotice({ title, description }: { title: string; description: string }) {
  return (
    <View style={styles.notice}>
      <Ionicons color={colors.textTertiary} name="alert-circle-outline" size={30} />
      <Text style={styles.noticeTitle}>{title}</Text>
      <Text style={styles.noticeDescription}>{description}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, overflow: 'hidden' },
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
