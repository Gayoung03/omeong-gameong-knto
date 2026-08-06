/** 반려동물 동반 가능 여부 */
export type PetPolicy = 'outdoorOnly' | 'indoorAllowed' | 'partialAllowed' | 'notAllowed';

/** 장소 분류 */
export type PlaceCategory = 'attraction' | 'restaurant' | 'cafe' | 'accommodation' | 'etc';

/** 일정 사이 이동 수단 */
export type TransportType = 'car' | 'walk' | 'ferry';

/** 여행 전체 이동 수단 */
export type TripTransport = 'rentalCar' | 'publicTransport' | 'ownCar' | 'walk';

/** 일정에 담긴 장소 요약 정보 */
export type SchedulePlace = {
  id: string;
  name: string;
  category: PlaceCategory;
  description: string;
  petPolicy: PetPolicy;
  address: string;
  rating: number | null;
  reviewCount: number;
  savedCount: number;
  imageUrl: string | null;
  latitude: number;
  longitude: number;
  isReservable: boolean;
};

/** 하루 일정 안의 개별 방문 항목 */
export type ScheduleItem = {
  id: string;
  order: number;
  place: SchedulePlace;
  isSaved: boolean;
  /** 방문 예정 시각 'HH:mm'. 정하지 않았으면 null */
  startTime: string | null;
  /** 이 방문에 대한 한 줄 메모. 없으면 빈 문자열 */
  memo: string;
  /** 다음 일정까지의 이동 정보. 마지막 항목이면 null */
  moveToNext: {
    transport: TransportType;
    distanceMeters: number;
    durationMinutes: number;
  } | null;
};

/** 날씨 상태 */
export type WeatherCondition = 'sunny' | 'partlyCloudy' | 'cloudy' | 'rainy' | 'snowy';

/** 시간대별 예보 한 칸 (기상청 단기예보 3시간 단위 기준) */
export type HourlyWeather = {
  /** HH:mm */
  time: string;
  condition: WeatherCondition;
  temperature: number;
  /** 강수 확률 (0~100) */
  precipitationProbability: number;
};

/** 하루치 날씨 요약 */
export type ScheduleWeather = {
  condition: WeatherCondition;
  /** 대표 기온 (낮 최고 기준) */
  temperature: number;
  minTemperature: number;
  maxTemperature: number;
  /** 시간대별 예보. 아직 받아오지 못했으면 빈 배열 */
  hourly: HourlyWeather[];
};

/** 날짜별 일정 */
export type Schedule = {
  id: string;
  dayNumber: number;
  /** YYYY-MM-DD */
  date: string;
  weather: ScheduleWeather | null;
  items: ScheduleItem[];
};

/** 여행 전체 이동 요약 */
export type TripDistanceSummary = {
  totalDistanceKm: number;
  carMinutes: number;
  walkMinutes: number;
};

/** 여행에 동행하는 반려동물 */
export type TripPet = {
  id: string;
  name: string;
  sizeType: 'small' | 'medium' | 'large';
  count: number;
};

/** 여행 전체 */
export type Trip = {
  id: string;
  title: string;
  /** YYYY-MM-DD */
  startDate: string;
  /** YYYY-MM-DD */
  endDate: string;
  nights: number;
  days: number;
  transport: TripTransport;
  pets: TripPet[];
  accommodationSummary: string;
  /** 여행 성향 한 줄 요약 (예: 여유로운 힐링 여행) */
  travelStyle: string;
  styleKeywords: string[];
  memo: string;
  coverEmoji: string;
  distanceSummary: TripDistanceSummary;
  schedules: Schedule[];
};

/** 체크리스트 항목 분류 */
export type ChecklistCategory = 'pet' | 'travel' | 'etc';

/** 여행 준비 체크리스트 항목 */
export type ChecklistItem = {
  id: string;
  category: ChecklistCategory;
  label: string;
  isChecked: boolean;
  /** 앱이 기본 제공한 추천 항목인지 여부 (사용자가 직접 추가한 항목과 구분) */
  isRecommended: boolean;
};

/** 날짜별 여행 메모 */
export type TripMemo = {
  id: string;
  /** 연결된 Schedule 의 id */
  scheduleId: string;
  title: string;
  content: string;
};

/** 여행 목록에서 사용하는 축약 정보 */
export type TripListItem = Pick<
  Trip,
  'id' | 'title' | 'startDate' | 'endDate' | 'nights' | 'days' | 'coverEmoji'
>;

/** 내 여행 상세 화면의 상단 탭 */
export type TripDetailTab = 'schedule' | 'map' | 'checklist' | 'memo';

/**
 * 일정 추가 화면에서 장소 목록을 가져오는 출처.
 *
 * - dayRecommend: 선택한 날짜의 루트 근처 추천
 * - recentSaved: 최근 저장한 장소
 * - nearStay: 이 여행의 숙소 근처 추천
 * - myPlace: 사용자가 직접 등록한 나만의 장소
 */
export type PlaceSourceTab = 'dayRecommend' | 'recentSaved' | 'nearStay' | 'myPlace';

/** 일정 추가 화면의 카테고리 필터. 선택하지 않으면 null */
export type PlaceFilter = 'restaurant' | 'attraction' | 'accommodation';

/**
 * 검색·추천 목록에 뜨는 장소 후보.
 *
 * 일정에 담기는 순간 `regionLabel` 을 떼고 `SchedulePlace` 로 저장한다.
 */
export type PlaceCandidate = SchedulePlace & {
  /** 목록에 짧게 노출하는 지역 이름 (예: 제주 시내) */
  regionLabel: string;
};

/**
 * 장소 선택 결과 규약.
 *
 * 지금은 trips 안의 임시 검색 화면이 이 값을 만들지만,
 * 나중에 places 검색 화면을 재사용하게 되면 그쪽에서도 이 형태로만 결과를 돌려받는다.
 * 장소 객체 전체가 아니라 ID 만 오간다.
 */
export type PlaceSelectionResult = {
  placeId: string;
};

/** 일정에 장소 하나를 담을 때 입력받는 값 */
export type AddScheduleInput = {
  /** 담을 날짜 (Schedule 의 id) */
  scheduleId: string;
  place: SchedulePlace;
  /** 'HH:mm'. 정하지 않았으면 null */
  startTime: string | null;
  memo: string;
};
