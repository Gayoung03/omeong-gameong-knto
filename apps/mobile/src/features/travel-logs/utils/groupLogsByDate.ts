import type { TravelLog } from '@/src/types/travelLog';

export type DateMemoryGroup = {
  date: string;
  /** 대표 선정 규칙: ① isRepresentative 지정 → ② 해당 날짜 최신 로그 → ③ 첫 로그 */
  representativeLog: TravelLog;
  otherLogs: TravelLog[];
};

/** 정렬 기준: visitedAt 우선, 없으면 createdAt */
function logTimestamp(log: TravelLog): string {
  return log.visitedAt ?? log.createdAt;
}

/**
 * 로그를 recordedDate 기준으로 묶는다. 같은 날짜라도 장소가 다르면
 * 그룹핑 목적상 하나의 날짜 그룹 안에서 개별 카드로 남는다(그룹핑은 날짜만 기준).
 * 로그가 없는 날짜 그룹은 애초에 생성되지 않는다.
 */
export function groupLogsByDate(logs: TravelLog[]): DateMemoryGroup[] {
  const byDate = new Map<string, TravelLog[]>();

  for (const log of logs) {
    const existing = byDate.get(log.recordedDate);
    if (existing) {
      existing.push(log);
    } else {
      byDate.set(log.recordedDate, [log]);
    }
  }

  const groups: DateMemoryGroup[] = [];

  for (const [date, dateLogs] of byDate) {
    const sorted = [...dateLogs].sort((a, b) => logTimestamp(a).localeCompare(logTimestamp(b)));
    const representativeLog =
      sorted.find((log) => log.isRepresentative) ?? sorted[sorted.length - 1] ?? sorted[0];
    const otherLogs = sorted.filter((log) => log.logId !== representativeLog.logId);

    groups.push({ date, representativeLog, otherLogs });
  }

  // 날짜 그룹 자체는 최근 날짜가 먼저 오도록 내림차순 정렬
  return groups.sort((a, b) => b.date.localeCompare(a.date));
}
