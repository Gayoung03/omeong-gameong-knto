import { useMemo } from 'react';

import type { KakaoPlaceMapProps } from './KakaoPlaceMap.types';
import { buildKakaoMapDocument } from './buildKakaoMapDocument';

import { HtmlFrame } from '@/src/components/web/HtmlFrame.web';
import { colors } from '@/src/theme';

export function KakaoPlaceMap({ appKey, places }: KakaoPlaceMapProps) {
  const document = useMemo(() => buildKakaoMapDocument(appKey, places), [appKey, places]);

  return (
    <HtmlFrame backgroundColor={colors.seaSoftLight} html={document} title="카카오 장소 지도" />
  );
}
