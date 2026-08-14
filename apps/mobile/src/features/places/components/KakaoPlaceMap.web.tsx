import { createElement, useMemo } from 'react';

import type { KakaoPlaceMapProps } from './KakaoPlaceMap.types';
import { buildKakaoMapDocument } from './buildKakaoMapDocument';

import { colors } from '@/src/theme';

export function KakaoPlaceMap({ appKey, places }: KakaoPlaceMapProps) {
  const document = useMemo(
    () => buildKakaoMapDocument(appKey, places),
    [appKey, places],
  );

  return createElement('iframe', {
    'aria-label': '카카오 장소 지도',
    srcDoc: document,
    style: {
      width: '100%',
      height: '100%',
      border: 0,
      backgroundColor: colors.seaSoftLight,
    },
    title: '카카오 장소 지도',
  });
}
