import { categoryColors, colors } from '@/src/theme';

import type { PlaceCategory } from '../types/trip';

/**
 * 장소 사진이 없을 때 쓰는 대체 썸네일.
 * 루트 추천 결과 화면이 이모지 + 파스텔 배경을 쓰고 있어 같은 방식으로 맞췄다.
 *
 * TODO: 장소 API 가 붙어 `imageUrl` 이 채워지면 실제 사진이 우선한다.
 */
export const placeThumbnails: Record<PlaceCategory, { background: string; emoji: string }> = {
  attraction: { background: categoryColors.leaf.bg, emoji: '🏞️' },
  restaurant: { background: categoryColors.orange.bg, emoji: '🍽️' },
  cafe: { background: categoryColors.yellow.bg, emoji: '☕' },
  accommodation: { background: categoryColors.blue.bg, emoji: '🏨' },
  etc: { background: colors.basaltSoft, emoji: '📍' },
};
