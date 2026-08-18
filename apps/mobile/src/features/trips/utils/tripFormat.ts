import { getPetPolicyLabel } from '@/src/types/place';

import type {
  PlaceCategory,
  ScheduleWeather,
  TransportType,
  Trip,
  WeatherCondition,
} from '../types/trip';

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

// 라벨 정본은 `src/types/place.ts` 에 있다. 기존 import 경로를 지키려고 여기서 다시 내보낸다.
export { getPetPolicyLabel };

const PLACE_CATEGORY_LABELS: Record<PlaceCategory, string> = {
  attraction: '관광지',
  restaurant: '음식점',
  cafe: '카페/디저트',
  accommodation: '숙소',
  etc: '기타',
};

export function getPlaceCategoryLabel(category: PlaceCategory): string {
  return PLACE_CATEGORY_LABELS[category];
}

/** '카페/디저트 · 제주 시내' */
export function formatPlaceMeta(category: PlaceCategory, regionLabel: string): string {
  return [getPlaceCategoryLabel(category), regionLabel].filter(Boolean).join(' · ');
}

/** '4.1(361)'. 평점이 없으면 null */
export function formatRating(rating: number | null, reviewCount: number): string | null {
  if (rating === null) {
    return null;
  }
  return `${rating.toFixed(1)}(${reviewCount.toLocaleString()})`;
}

/** '저장 8,903' */
export function formatSavedCount(savedCount: number): string {
  return `저장 ${savedCount.toLocaleString()}`;
}

/** Date → 'HH:mm' */
export function toTimeValue(date: Date): string {
  const hours = `${date.getHours()}`.padStart(2, '0');
  const minutes = `${date.getMinutes()}`.padStart(2, '0');
  return `${hours}:${minutes}`;
}

/** 'HH:mm' 을 오늘 날짜의 Date 로 변환. 형식이 어긋나면 기본값(09:00) */
export function parseTimeValue(timeString: string | null): Date {
  const date = new Date();
  const [hours, minutes] = (timeString ?? '09:00').split(':').map(Number);

  date.setHours(Number.isFinite(hours) ? hours : 9, Number.isFinite(minutes) ? minutes : 0, 0, 0);
  return date;
}

/** '오후 2:30' */
export function formatTimeLabel(timeString: string): string {
  const [hours, minutes] = timeString.split(':').map(Number);
  const meridiem = hours < 12 ? '오전' : '오후';
  const displayHour = hours % 12 === 0 ? 12 : hours % 12;

  return `${meridiem} ${displayHour}:${`${minutes}`.padStart(2, '0')}`;
}

const WEATHER_ICONS: Record<WeatherCondition, string> = {
  sunny: '☀️',
  partlyCloudy: '⛅',
  cloudy: '☁️',
  rainy: '🌧️',
  snowy: '❄️',
};

export function getWeatherIcon(condition: WeatherCondition): string {
  return WEATHER_ICONS[condition];
}

const WEATHER_LABELS: Record<WeatherCondition, string> = {
  sunny: '맑음',
  partlyCloudy: '구름 조금',
  cloudy: '흐림',
  rainy: '비',
  snowy: '눈',
};

export function getWeatherLabel(condition: WeatherCondition): string {
  return WEATHER_LABELS[condition];
}

/** 최저·최고 기온 요약 (예: 24° / 31°) */
export function formatTemperatureRange(weather: ScheduleWeather): string {
  return `${weather.minTemperature}° / ${weather.maxTemperature}°`;
}

/** 하루 중 가장 높은 강수 확률 */
export function getMaxPrecipitationProbability(weather: ScheduleWeather): number {
  if (weather.hourly.length === 0) {
    return 0;
  }
  return Math.max(...weather.hourly.map((hour) => hour.precipitationProbability));
}

/** 산책 팁의 강조 수준 */
export type PetWalkTipTone = 'caution' | 'watch' | 'good';

/** 반려동물 산책 팁 */
export type PetWalkTip = {
  tone: PetWalkTipTone;
  title: string;
  description: string;
};

/**
 * 날씨와 기온으로 반려동물 산책 팁을 만든다.
 * 위험한 조건(눈·비·폭염·한파)을 먼저 확인하고, 해당 없으면 좋은 날씨로 안내한다.
 */
export function getPetWalkTip(condition: WeatherCondition, temperature: number): PetWalkTip {
  if (condition === 'snowy') {
    return {
      tone: 'caution',
      title: '눈길 산책은 짧게',
      description: '발바닥 사이에 눈이 뭉칠 수 있어요. 산책 후 발과 배를 미지근한 물로 닦아주세요.',
    };
  }

  if (condition === 'rainy') {
    return {
      tone: 'watch',
      title: '비 소식이 있어요',
      description: '레인코트와 여분 수건을 챙기고, 실내 동반이 가능한 장소 위주로 움직여보세요.',
    };
  }

  if (temperature >= 31) {
    return {
      tone: 'caution',
      title: '한낮 아스팔트 화상 주의',
      description:
        '달궈진 바닥에 발바닥을 델 수 있어요. 오전 8시 이전이나 해가 진 뒤에 산책하는 걸 권해요.',
    };
  }

  if (temperature >= 27) {
    return {
      tone: 'watch',
      title: '더위에 지치기 쉬워요',
      description:
        '10분마다 그늘에서 쉬고 물을 자주 주세요. 헐떡임이 심해지면 바로 실내로 이동해요.',
    };
  }

  if (temperature <= 0) {
    return {
      tone: 'caution',
      title: '한파에 체온이 빨리 떨어져요',
      description: '산책을 짧게 나누어 하고, 소형견·단모종은 옷을 꼭 입혀주세요.',
    };
  }

  if (temperature <= 8) {
    return {
      tone: 'watch',
      title: '쌀쌀한 날씨예요',
      description: '노령견과 소형견은 추위에 약해요. 산책 시간을 30분 안쪽으로 줄여주세요.',
    };
  }

  return {
    tone: 'good',
    title: '산책하기 좋은 날씨예요',
    description: '기온이 적당해요. 물만 챙기면 바깥 일정을 소화하는 데 무리가 없어요.',
  };
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
