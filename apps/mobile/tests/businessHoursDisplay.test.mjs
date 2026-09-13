import assert from 'node:assert/strict';
import test from 'node:test';

import {
  toBusinessHoursDisplay,
  toClosedDaysDisplay,
} from '../src/features/places/api/businessHoursDisplay.ts';

const repeatedHours = Array.from({ length: 7 }, (_, dayOfWeek) => ({
  closesAt: null,
  dayOfWeek,
  isClosed: false,
  opensAt: null,
  rawText: '매일 00:00~24:00\n정기휴일 연중무휴',
}));

test('반복된 매일 운영시간과 휴무일을 한 번씩만 표시한다', () => {
  assert.equal(toBusinessHoursDisplay(null, repeatedHours), '매일 00:00~24:00');
  assert.equal(toClosedDaysDisplay(null, null, repeatedHours), '연중무휴');
});

test('DB의 요일별 시간과 휴무 값을 그대로 표시한다', () => {
  const hours = [
    {
      closesAt: '18:30:00',
      dayOfWeek: 1,
      isClosed: false,
      opensAt: '09:15:00',
      rawText: null,
    },
    {
      closesAt: null,
      dayOfWeek: 2,
      isClosed: true,
      opensAt: null,
      rawText: null,
    },
  ];

  assert.equal(toBusinessHoursDisplay(null, hours), '월 09:15~18:30\n화 휴무');
});
