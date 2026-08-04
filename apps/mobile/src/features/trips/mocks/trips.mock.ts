import type {
  HourlyWeather,
  Schedule,
  ScheduleItem,
  SchedulePlace,
  ScheduleWeather,
  Trip,
  WeatherCondition,
} from '../types/trip';

type PlaceSeed = Omit<SchedulePlace, 'imageUrl' | 'isReservable'> &
  Partial<Pick<SchedulePlace, 'imageUrl' | 'isReservable'>>;

function createPlace(seed: PlaceSeed): SchedulePlace {
  return {
    imageUrl: null,
    isReservable: false,
    ...seed,
  };
}

const places = {
  hyeopjae: createPlace({
    id: 'place-hyeopjae',
    name: '협재해수욕장',
    category: 'attraction',
    description: '에메랄드빛 바다와 하얀 모래사장, 반려견 동반 산책이 가능한 해변',
    petPolicy: 'outdoorOnly',
    address: '제주시 한림읍',
    rating: 4.6,
    reviewCount: 4283,
    savedCount: 22368,
    latitude: 33.3939,
    longitude: 126.2396,
  }),
  aewolCafe: createPlace({
    id: 'place-aewol-cafe',
    name: '애월 카페거리',
    category: 'cafe',
    description: '오션뷰 카페에서 여유로운 브런치 타임',
    petPolicy: 'indoorAllowed',
    address: '제주시 애월읍',
    rating: 4.4,
    reviewCount: 1920,
    savedCount: 15400,
    latitude: 33.4636,
    longitude: 126.3096,
    isReservable: true,
  }),
  hallimPark: createPlace({
    id: 'place-hallim-park',
    name: '한림공원',
    category: 'attraction',
    description: '다양한 테마 정원 산책',
    petPolicy: 'outdoorOnly',
    address: '제주시 한림읍',
    rating: 4.3,
    reviewCount: 3110,
    savedCount: 9800,
    latitude: 33.3894,
    longitude: 126.2408,
  }),
  osulloc: createPlace({
    id: 'place-osulloc',
    name: '오설록 티뮤지엄',
    category: 'attraction',
    description: '녹차밭과 전시 관람',
    petPolicy: 'partialAllowed',
    address: '서귀포시 안덕면',
    rating: 4.5,
    reviewCount: 5620,
    savedCount: 31200,
    latitude: 33.3057,
    longitude: 126.2896,
  }),
  seongsan: createPlace({
    id: 'place-seongsan',
    name: '성산일출봉',
    category: 'attraction',
    description: '일몰이 아름다운 뷰 포인트',
    petPolicy: 'outdoorOnly',
    address: '서귀포시 성산읍',
    rating: 4.7,
    reviewCount: 8240,
    savedCount: 45100,
    latitude: 33.4581,
    longitude: 126.9427,
  }),
  jungmun: createPlace({
    id: 'place-jungmun',
    name: '중문색달해변',
    category: 'attraction',
    description: '파도가 시원한 남쪽 해변 산책 코스',
    petPolicy: 'outdoorOnly',
    address: '서귀포시 색달동',
    rating: 4.4,
    reviewCount: 2870,
    savedCount: 12600,
    latitude: 33.2447,
    longitude: 126.4108,
  }),
  cheonjiyeon: createPlace({
    id: 'place-cheonjiyeon',
    name: '천지연폭포',
    category: 'attraction',
    description: '산책로가 잘 정비된 폭포 명소',
    petPolicy: 'outdoorOnly',
    address: '서귀포시 천지동',
    rating: 4.5,
    reviewCount: 6120,
    savedCount: 20400,
    latitude: 33.2468,
    longitude: 126.5543,
  }),
  udo: createPlace({
    id: 'place-udo',
    name: '우도',
    category: 'attraction',
    description: '배편 이용 시 반려동물 켄넬 필수',
    petPolicy: 'partialAllowed',
    address: '제주시 우도면',
    rating: 4.6,
    reviewCount: 7310,
    savedCount: 28800,
    latitude: 33.5064,
    longitude: 126.9526,
  }),
  seongsanStay: createPlace({
    id: 'place-seongsan-stay',
    name: '숲 게스트하우스 성산점',
    category: 'accommodation',
    description: '반려동물 동반 가능한 독채형 숙소',
    petPolicy: 'indoorAllowed',
    address: '서귀포시 성산읍',
    rating: 4.8,
    reviewCount: 640,
    savedCount: 3200,
    latitude: 33.4602,
    longitude: 126.9312,
    isReservable: true,
  }),
  dodubong: createPlace({
    id: 'place-dodubong',
    name: '도두봉',
    category: 'attraction',
    description: '비행기와 푸른 바다가 어우러진 장관을 자랑하는 오름',
    petPolicy: 'outdoorOnly',
    address: '제주시 도두일동',
    rating: 4.4,
    reviewCount: 1271,
    savedCount: 12480,
    latitude: 33.5107,
    longitude: 126.4666,
  }),
  jejuAirport: createPlace({
    id: 'place-jeju-airport',
    name: '제주국제공항',
    category: 'etc',
    description: '반려동물 체크인은 출발 2시간 전까지',
    petPolicy: 'partialAllowed',
    address: '제주시 용담이동',
    rating: 4.1,
    reviewCount: 12800,
    savedCount: 52000,
    latitude: 33.5113,
    longitude: 126.4929,
  }),
} satisfies Record<string, SchedulePlace>;

type ItemSeed = {
  place: SchedulePlace;
  isSaved?: boolean;
  moveToNext?: ScheduleItem['moveToNext'];
};

function createItems(seeds: ItemSeed[]): ScheduleItem[] {
  return seeds.map((seed, index) => ({
    id: `${seed.place.id}-item`,
    order: index + 1,
    place: seed.place,
    isSaved: seed.isSaved ?? false,
    moveToNext: seed.moveToNext ?? null,
  }));
}

/** 기상청 단기예보와 동일하게 3시간 간격으로 제공한다 */
const FORECAST_TIMES = ['06:00', '09:00', '12:00', '15:00', '18:00', '21:00'] as const;

/** [날씨, 기온, 강수확률] 을 FORECAST_TIMES 순서대로 나열한 값 */
type HourlySeed = [WeatherCondition, number, number];

function createWeather(condition: WeatherCondition, seeds: HourlySeed[]): ScheduleWeather {
  const hourly: HourlyWeather[] = seeds.map(
    ([hourCondition, temperature, precipitationProbability], index) => ({
      time: FORECAST_TIMES[index],
      condition: hourCondition,
      temperature,
      precipitationProbability,
    }),
  );
  const temperatures = hourly.map((item) => item.temperature);
  const maxTemperature = Math.max(...temperatures);

  return {
    condition,
    temperature: maxTemperature,
    minTemperature: Math.min(...temperatures),
    maxTemperature,
    hourly,
  };
}

const schedules: Schedule[] = [
  {
    id: 'schedule-day-1',
    dayNumber: 1,
    date: '2026-07-31',
    weather: createWeather('sunny', [
      ['sunny', 25, 0],
      ['sunny', 28, 0],
      ['sunny', 31, 10],
      ['sunny', 31, 10],
      ['partlyCloudy', 29, 10],
      ['partlyCloudy', 26, 0],
    ]),
    items: createItems([
      {
        place: places.hyeopjae,
        isSaved: true,
        moveToNext: { transport: 'car', distanceMeters: 3100, durationMinutes: 9 },
      },
      {
        place: places.aewolCafe,
        moveToNext: { transport: 'walk', distanceMeters: 286, durationMinutes: 4 },
      },
      {
        place: places.hallimPark,
        moveToNext: { transport: 'car', distanceMeters: 7200, durationMinutes: 15 },
      },
      {
        place: places.osulloc,
        moveToNext: { transport: 'car', distanceMeters: 5700, durationMinutes: 12 },
      },
      { place: places.seongsan },
    ]),
  },
  {
    id: 'schedule-day-2',
    dayNumber: 2,
    date: '2026-08-01',
    weather: createWeather('partlyCloudy', [
      ['partlyCloudy', 25, 10],
      ['partlyCloudy', 27, 20],
      ['cloudy', 30, 30],
      ['cloudy', 30, 40],
      ['partlyCloudy', 28, 20],
      ['partlyCloudy', 25, 10],
    ]),
    items: createItems([
      {
        place: places.jungmun,
        moveToNext: { transport: 'car', distanceMeters: 12400, durationMinutes: 22 },
      },
      {
        place: places.cheonjiyeon,
        moveToNext: { transport: 'car', distanceMeters: 41200, durationMinutes: 58 },
      },
      { place: places.seongsanStay },
    ]),
  },
  {
    id: 'schedule-day-3',
    dayNumber: 3,
    date: '2026-08-02',
    weather: createWeather('rainy', [
      ['cloudy', 24, 30],
      ['cloudy', 26, 40],
      ['rainy', 28, 70],
      ['rainy', 29, 80],
      ['cloudy', 27, 50],
      ['cloudy', 25, 30],
    ]),
    items: createItems([
      {
        place: places.udo,
        moveToNext: { transport: 'ferry', distanceMeters: 3800, durationMinutes: 15 },
      },
      { place: places.seongsanStay },
    ]),
  },
  {
    id: 'schedule-day-4',
    dayNumber: 4,
    date: '2026-08-03',
    weather: createWeather('sunny', [
      ['sunny', 26, 0],
      ['sunny', 29, 0],
      ['sunny', 31, 0],
      ['sunny', 31, 10],
      ['sunny', 29, 0],
      ['partlyCloudy', 27, 0],
    ]),
    items: createItems([
      {
        place: places.dodubong,
        moveToNext: { transport: 'car', distanceMeters: 5400, durationMinutes: 13 },
      },
      { place: places.jejuAirport },
    ]),
  },
];

export const MOCK_TRIP: Trip = {
  id: 'trip-jeju-mong',
  title: '몽이와 떠나는 제주 여행',
  startDate: '2026-07-31',
  endDate: '2026-08-03',
  nights: 3,
  days: 4,
  transport: 'rentalCar',
  pets: [{ id: 'pet-mong', name: '몽이', sizeType: 'small', count: 1 }],
  accommodationSummary: '성산 숙소 2곳',
  travelStyle: '여유로운 힐링 여행',
  styleKeywords: ['바다', '카페', '산책로', '자연'],
  memo: '바다 산책을 좋아하는 몽이를 위한 여유로운 코스! 실내 일정은 반려동물 동반 가능 여부 미리 확인하기',
  coverEmoji: '🐶',
  distanceSummary: { totalDistanceKm: 86.7, carMinutes: 205, walkMinutes: 100 },
  schedules,
};

export const MOCK_TRIPS: Trip[] = [MOCK_TRIP];
