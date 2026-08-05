const toCalendarUtc = (date: Date) =>
  Date.UTC(date.getFullYear(), date.getMonth(), date.getDate());

export const getTripDayCount = (startAt: string, endAt: string) => {
  const start = new Date(startAt);
  const end = new Date(endAt);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) {
    return 0;
  }

  const calendarDifference = Math.round(
    (toCalendarUtc(end) - toCalendarUtc(start)) / (24 * 60 * 60 * 1000),
  );
  return calendarDifference + 1;
};

export const formatTripDuration = (startAt: string, endAt: string) => {
  const days = getTripDayCount(startAt, endAt);
  if (days <= 0) return '일정 확인 필요';
  return days === 1 ? '당일치기' : `${days - 1}박 ${days}일`;
};

export const getTripDates = (startAt: string, endAt: string) => {
  const dayCount = getTripDayCount(startAt, endAt);
  if (dayCount === 0) return [];

  const start = new Date(startAt);
  return Array.from({ length: dayCount }, (_, index) => {
    const date = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    date.setDate(date.getDate() + index);
    return date;
  });
};

export const formatRouteDate = (date: Date) =>
  `${date.getMonth() + 1}월 ${date.getDate()}일`;
