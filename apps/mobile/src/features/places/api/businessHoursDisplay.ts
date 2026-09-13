type BusinessHour = {
  dayOfWeek: number;
  isClosed: boolean;
  opensAt: string | null;
  closesAt: string | null;
  rawText: string | null;
};

const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'];
const CLOSED_DAY_LINE = /^(?:정기\s*휴일|휴무일)\s*:?\s*(.*)$/;

function splitRawText(rawText: string | null): { closedDays: string[]; hours: string[] } {
  const closedDays: string[] = [];
  const hours: string[] = [];

  for (const line of rawText?.split(/\r?\n/) ?? []) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const closedDay = trimmed.match(CLOSED_DAY_LINE);
    if (closedDay) {
      if (closedDay[1]) closedDays.push(closedDay[1]);
    } else {
      hours.push(trimmed);
    }
  }
  return { closedDays, hours };
}

export function toBusinessHoursDisplay(
  businessHoursRaw: string | null,
  businessHours: BusinessHour[],
): string | null {
  if (businessHoursRaw) {
    const unique = [...new Set(splitRawText(businessHoursRaw).hours)];
    return unique.join('\n') || null;
  }

  const entries = businessHours
    .map((hour) => {
      const rawHours = splitRawText(hour.rawText).hours.join(' ');
      if (rawHours) return { day: hour.dayOfWeek, text: rawHours };
      if (hour.isClosed) return { day: hour.dayOfWeek, text: '휴무' };
      if (hour.opensAt && hour.closesAt) {
        return {
          day: hour.dayOfWeek,
          text: `${hour.opensAt.slice(0, 5)}~${hour.closesAt.slice(0, 5)}`,
        };
      }
      return null;
    })
    .filter((entry): entry is { day: number; text: string } => entry !== null);

  const coversEveryDay = new Set(entries.map((entry) => entry.day)).size === 7;
  const uniqueTimes = [...new Set(entries.map((entry) => entry.text))];
  if (coversEveryDay && uniqueTimes.length === 1) {
    const time = uniqueTimes[0];
    return time.startsWith('매일') ? time : `매일 ${time}`;
  }

  return (
    entries
      .map(({ day, text }) => `${DAY_LABELS[day] ?? day} ${text}`)
      .filter((line, index, lines) => lines.indexOf(line) === index)
      .join('\n') || null
  );
}

export function toClosedDaysDisplay(
  closedDaysRaw: string | null,
  businessHoursRaw: string | null,
  businessHours: BusinessHour[],
): string | null {
  if (closedDaysRaw?.trim()) return closedDaysRaw.trim().replace(CLOSED_DAY_LINE, '$1');

  const closedDays = [
    ...splitRawText(businessHoursRaw).closedDays,
    ...businessHours.flatMap((hour) => splitRawText(hour.rawText).closedDays),
  ];
  return [...new Set(closedDays)].join(', ') || null;
}
