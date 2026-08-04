import type { PetPolicy, ScheduleWeather, TransportType, Trip } from '../types/trip';

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'] as const;

/** 'YYYY-MM-DD' 를 로컬 기준 Date 로 변환 */
export function parseDate(dateString: string): Date {
  const [year, month, day] = dateString.split('-').map(Number);
  return new Date(year, month - 1, day);
}

/** Date → 'YYYY-MM-DD' */
export function toDateValue(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

/** 시작·종료일로 박/일 수 계산 */
export function calculateTripLength(
  startDate: string,
  endDate: string,
): {
  nights: number;
  days: number;
} {
  const MS_PER_DAY = 1000 * 60 * 60 * 24;
  const diffDays = Math.round(
    (parseDate(endDate).getTime() - parseDate(startDate).getTime()) / MS_PER_DAY,
  );
  const nights = Math.max(diffDays, 0);

  return { nights, days: nights + 1 };
}

/** '07.31(금)' */
export function formatMonthDay(dateString: string): string {
  const date = parseDate(dateString);
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${month}.${day}(${WEEKDAY_LABELS[date.getDay()]})`;
}

/** '2026.07.31 금요일' */
export function formatFullDate(dateString: string): string {
  const date = parseDate(dateString);
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${date.getFullYear()}.${month}.${day} ${WEEKDAY_LABELS[date.getDay()]}요일`;
}

/** '2026.07.31(금) ~ 08.03(월) · 3박 4일' */
export function formatTripPeriod(
  trip: Pick<Trip, 'startDate' | 'endDate' | 'nights' | 'days'>,
): string {
  const start = parseDate(trip.startDate);
  const startText = `${start.getFullYear()}.${formatMonthDay(trip.startDate)}`;
  return `${startText} ~ ${formatMonthDay(trip.endDate)} · ${trip.nights}박 ${trip.days}일`;
}

/** '3.1km' 또는 '286m' */
export function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${meters}m`;
  }
  return `${(meters / 1000).toFixed(1)}km`;
}

/** '3시간 25분' 또는 '25분' */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const restMinutes = minutes % 60;

  if (hours === 0) {
    return `${restMinutes}분`;
  }
  if (restMinutes === 0) {
    return `${hours}시간`;
  }
  return `${hours}시간 ${restMinutes}분`;
}

const TRANSPORT_LABELS: Record<TransportType, string> = {
  car: '차량',
  walk: '도보',
  ferry: '배',
};

/** '3.1km · 차량 9분' */
export function formatMoveInfo(
  transport: TransportType,
  distanceMeters: number,
  durationMinutes: number,
): string {
  return `${formatDistance(distanceMeters)} · ${TRANSPORT_LABELS[transport]} ${durationMinutes}분`;
}

const PET_POLICY_LABELS: Record<PetPolicy, string> = {
  outdoorOnly: '야외 · 목줄 필수',
  indoorAllowed: '실내 동반 가능',
  partialAllowed: '일부 구역 동반',
  notAllowed: '동반 불가',
};

export function getPetPolicyLabel(petPolicy: PetPolicy): string {
  return PET_POLICY_LABELS[petPolicy];
}

const WEATHER_ICONS: Record<ScheduleWeather['condition'], string> = {
  sunny: '☀️',
  partlyCloudy: '⛅',
  cloudy: '☁️',
  rainy: '🌧️',
  snowy: '❄️',
};

export function getWeatherIcon(condition: ScheduleWeather['condition']): string {
  return WEATHER_ICONS[condition];
}

const TRIP_TRANSPORT_LABELS: Record<Trip['transport'], string> = {
  rentalCar: '렌터카',
  publicTransport: '대중교통',
  ownCar: '자차',
  walk: '도보',
};

const PET_SIZE_LABELS: Record<Trip['pets'][number]['sizeType'], string> = {
  small: '소형견',
  medium: '중형견',
  large: '대형견',
};

export function getTransportLabel(transport: Trip['transport']): string {
  return TRIP_TRANSPORT_LABELS[transport];
}

/** '몽이(소형견) 1마리' */
export function formatPets(pets: Trip['pets']): string {
  return pets
    .map((pet) => `${pet.name}(${PET_SIZE_LABELS[pet.sizeType]}) ${pet.count}마리`)
    .join(', ');
}

/** '렌터카 · 몽이(소형견) 1마리 · 성산 숙소 2곳' */
export function formatTripTags(trip: Trip): string {
  return [getTransportLabel(trip.transport), formatPets(trip.pets), trip.accommodationSummary]
    .filter(Boolean)
    .join(' · ');
}
