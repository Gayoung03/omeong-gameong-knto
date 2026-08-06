import type { DateRange, UngroupedLogGroup } from '@/src/types/travelLog';

/** Date 객체를 ISO 날짜 문자열(YYYY-MM-DD)로 변환한다. 로컬 타임존 기준. */
export function toIsoDate(date: Date): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** ISO 날짜 문자열 사이의 모든 날짜를 순서대로 반환한다. */
export function eachDayInRange(range: DateRange): string[] {
  const days: string[] = [];
  const cursor = new Date(`${range.start}T00:00:00`);
  const last = new Date(`${range.end}T00:00:00`);

  while (cursor <= last) {
    days.push(toIsoDate(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }

  return days;
}

/** 이번 달 1일 ~ 말일 */
export function getCurrentMonthRange(today = new Date()): DateRange {
  const start = new Date(today.getFullYear(), today.getMonth(), 1);
  const end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  return { start: toIsoDate(start), end: toIsoDate(end) };
}

/** 오늘로부터 최근 3개월 (오늘 포함) */
export function getRecentThreeMonthsRange(today = new Date()): DateRange {
  const start = new Date(today.getFullYear(), today.getMonth() - 2, 1);
  return { start: toIsoDate(start), end: toIsoDate(today) };
}

/** 미연결 기록 그룹이 속한 월의 시작일~말일 범위 */
export function getGroupMonthRange(group: UngroupedLogGroup): DateRange {
  const start = new Date(group.year, group.month - 1, 1);
  const end = new Date(group.year, group.month, 0);
  return { start: toIsoDate(start), end: toIsoDate(end) };
}

/** "2026.08.02 – 08.04" 형태. 연도가 다르면 종료일에도 연도를 표시한다. */
export function formatDateRangeLabel(range: DateRange): string {
  const [startYear, startMonth, startDay] = range.start.split('-');
  const [endYear, endMonth, endDay] = range.end.split('-');

  const startLabel = `${startYear}.${startMonth}.${startDay}`;

  if (range.start === range.end) {
    return startLabel;
  }

  const endLabel =
    startYear === endYear ? `${endMonth}.${endDay}` : `${endYear}.${endMonth}.${endDay}`;

  return `${startLabel} – ${endLabel}`;
}

/** "2026년 8월" */
export function formatMonthLabel(year: number, month: number): string {
  return `${year}년 ${month}월`;
}

/** "2026.08.04" */
export function formatShortDate(recordedDate: string): string {
  const [year, month, day] = recordedDate.split('-');
  return `${year}.${month}.${day}`;
}

/** "8월 4일" — 지역명을 포함하지 않는 날짜 그룹 제목용 */
export function formatDayTitle(recordedDate: string): string {
  const [, month, day] = recordedDate.split('-');
  return `${Number(month)}월 ${Number(day)}일`;
}
