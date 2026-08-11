import type { TripMemo } from '../types/trip';

export const MOCK_MEMOS: TripMemo[] = [
  {
    id: 'memo-day-1',
    scheduleId: 'schedule-day-1',
    title: '협재 → 애월 서쪽 코스',
    content:
      '협재는 오전이 한산해요. 몽이 산책은 9시 전에!\n애월 브런치 카페는 소형견 동반 가능 (예약 필수)',
  },
  {
    id: 'memo-day-2',
    scheduleId: 'schedule-day-2',
    title: '중문 · 서귀포 코스',
    content: '오설록은 야외 정원만 동반 가능\n점심은 도시락 챙겨서 피크닉',
  },
  {
    id: 'memo-day-3',
    scheduleId: 'schedule-day-3',
    title: '성산 · 우도 코스',
    content: '우도 배편은 반려동물 켄넬 필수!\n성산 숙소 체크인 15시부터',
  },
];
