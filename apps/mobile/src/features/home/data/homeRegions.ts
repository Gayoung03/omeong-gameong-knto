import type { PlaceRegion } from '@/src/features/places/types/place';

type PercentagePosition = `${number}%`;

export type HomeRegion = {
  id: string;
  label: PlaceRegion;
  left: PercentagePosition;
  top: PercentagePosition;
};

export const homeRegions: HomeRegion[] = [
  {
    id: 'aewol-hallim-hyeopjae',
    label: '애월/한림/협재',
    left: '25%',
    top: '32%',
  },
  {
    id: 'jeju-airport',
    label: '제주시/제주국제공항',
    left: '49%',
    top: '27%',
  },
  {
    id: 'hamdeok-gimnyeong-sehwa',
    label: '함덕/김녕/세화',
    left: '74%',
    top: '31%',
  },
  {
    id: 'seogwipo-moseulpo',
    label: '서귀포시/모슬포',
    left: '27%',
    top: '68%',
  },
  {
    id: 'jungmun',
    label: '중문',
    left: '50%',
    top: '69%',
  },
  {
    id: 'pyoseon-seongsan',
    label: '표선/성산',
    left: '74%',
    top: '65%',
  },
];
