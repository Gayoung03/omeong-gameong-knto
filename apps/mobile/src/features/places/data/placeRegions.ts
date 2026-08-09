import type { PlaceRegion } from '../types/place';

export const placeRegions = [
  '전체',
  '제주시/제주국제공항',
  '서귀포시/모슬포',
  '애월/한림/협재',
  '중문',
  '표선/성산',
  '함덕/김녕/세화',
] as const;

export type PlaceRegionFilter = (typeof placeRegions)[number];

export function isPlaceRegion(value: string): value is PlaceRegion {
  return placeRegions.includes(value as PlaceRegionFilter) && value !== '전체';
}
