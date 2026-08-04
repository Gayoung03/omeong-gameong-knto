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
  /** 다음 일정까지의 이동 정보. 마지막 항목이면 null */
  moveToNext: {
    transport: TransportType;
    distanceMeters: number;
    durationMinutes: number;
  } | null;
};

/** 하루치 날씨 요약 */
export type ScheduleWeather = {
  condition: 'sunny' | 'partlyCloudy' | 'cloudy' | 'rainy' | 'snowy';
  temperature: number;
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
