import assert from 'node:assert/strict';
import test from 'node:test';

import { weatherTip } from './weatherCopy.ts';

test('강수확률이 높으면 비 안내를 우선한다', () => {
  assert.match(
    weatherTip({
      condition: 'cloudy',
      temperature: 24,
      precipitationProbability: 70,
      windSpeed: 3,
    }),
    /우산/,
  );
});
