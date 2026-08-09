import type {
  TravelLog,
  TravelLogListItem,
  TravelLogPetSnapshot,
  Trip,
  UngroupedLogGroup,
} from '@/src/types/travelLog';

const PET_IMAGE = 'https://placehold.co/200x200';

/**
 * 기록 당시의 반려동물 스냅샷. 살아있는 Pet 데이터를 참조하지 않으므로
 * 이후 프로필을 수정하거나 지워도 과거 기록의 표시 내용은 그대로 유지된다.
 */
const MONGI: TravelLogPetSnapshot = {
  petId: 'pet-1',
  nameSnapshot: '몽이',
  profileImageSnapshot: PET_IMAGE,
};

const KOKO: TravelLogPetSnapshot = {
  petId: 'pet-2',
  nameSnapshot: '코코',
  profileImageSnapshot: PET_IMAGE,
};

function generatedImage(seed: string): string {
  return `https://placehold.co/800x800/FFF3EA/FF8A3D?text=${encodeURIComponent(seed)}`;
}

function originalImage(seed: string): string {
  return `https://placehold.co/800x800/EEEEEA/7A7A7A?text=${encodeURIComponent(`원본 ${seed}`)}`;
}

type TripMeta = {
  tripId: string;
  title: string;
  placeName: string;
  startDate: string;
  endDate: string;
  companions: TravelLogPetSnapshot[];
};

const tripMetaList: TripMeta[] = [
  {
    tripId: 'trip-1',
    title: '애월 2박 3일 여행',
    placeName: '애월',
    startDate: '2026-08-02',
    endDate: '2026-08-04',
    companions: [MONGI],
  },
  {
    tripId: 'trip-2',
    title: '한림 여름 여행',
    placeName: '한림',
    startDate: '2026-07-29',
    endDate: '2026-07-31',
    companions: [MONGI],
  },
  {
    tripId: 'trip-3',
    title: '성산 일출 여행',
    placeName: '성산',
    startDate: '2026-06-12',
    endDate: '2026-06-14',
    companions: [MONGI, KOKO],
  },
  {
    tripId: 'trip-4',
    title: '서귀포 봄 산책',
    placeName: '서귀포',
    startDate: '2026-04-05',
    endDate: '2026-04-06',
    companions: [KOKO],
  },
];

/**
 * 목업 로그 원본 데이터. Trip의 logCount·미리보기 사진은 전부 이 배열에서 계산해,
 * 메인 화면 콜라주와 여행 모아보기 팝업이 서로 다른 이미지를 가리키는 일이 없도록 한다.
 */
export const mockLogs: TravelLog[] = [
  // 애월 2박 3일 여행 (trip-1) — 8개
  {
    logId: 'log-1-1',
    tripId: 'trip-1',
    recordedDate: '2026-08-04',
    visitedAt: '2026-08-04T18:30:00',
    createdAt: '2026-08-04T18:40:00',
    placeId: 'place-aewol-beach',
    placeName: '애월 해변',
    originalImageUrl: originalImage('애월 해변'),
    generatedImageUrl: generatedImage('애월 해변'),
    personalMessage: '몽이와 처음 본 제주 바다.\n오래 기억하고 싶은 저녁이었다.',
    companions: [MONGI],
    isRepresentative: true,
  },
  {
    logId: 'log-1-2',
    tripId: 'trip-1',
    recordedDate: '2026-08-04',
    visitedAt: '2026-08-04T15:00:00',
    createdAt: '2026-08-04T15:10:00',
    placeId: 'place-aewol-cafe',
    placeName: '애월 해안도로 카페',
    originalImageUrl: originalImage('카페'),
    generatedImageUrl: generatedImage('카페'),
    personalMessage: '해변 앞 카페에서 몽이랑 한 컷',
    companions: [MONGI],
    isRepresentative: false,
  },
  {
    logId: 'log-1-3',
    tripId: 'trip-1',
    recordedDate: '2026-08-04',
    visitedAt: '2026-08-04T11:00:00',
    createdAt: '2026-08-04T11:05:00',
    placeId: 'place-gwakji-beach',
    placeName: '곽지해수욕장',
    originalImageUrl: originalImage('곽지'),
    generatedImageUrl: generatedImage('곽지'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },
  {
    logId: 'log-1-4',
    tripId: 'trip-1',
    recordedDate: '2026-08-04',
    visitedAt: '2026-08-04T09:00:00',
    createdAt: '2026-08-04T09:05:00',
    placeId: 'place-hyeopjae-beach',
    placeName: '협재해수욕장',
    originalImageUrl: originalImage('협재'),
    generatedImageUrl: generatedImage('협재'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },
  {
    logId: 'log-1-5',
    tripId: 'trip-1',
    recordedDate: '2026-08-03',
    visitedAt: '2026-08-03T17:00:00',
    createdAt: '2026-08-03T17:10:00',
    placeId: 'place-handam-trail',
    placeName: '한담해안산책로',
    originalImageUrl: originalImage('한담'),
    generatedImageUrl: generatedImage('한담'),
    personalMessage: '몽이가 제일 좋아한 산책로',
    companions: [MONGI],
    isRepresentative: true,
  },
  {
    logId: 'log-1-6',
    tripId: 'trip-1',
    recordedDate: '2026-08-03',
    visitedAt: '2026-08-03T09:30:00',
    createdAt: '2026-08-03T09:35:00',
    placeId: 'place-stay-yard',
    placeName: '숙소 마당',
    originalImageUrl: originalImage('숙소'),
    generatedImageUrl: generatedImage('숙소'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },
  {
    logId: 'log-1-7',
    tripId: 'trip-1',
    recordedDate: '2026-08-02',
    visitedAt: '2026-08-02T14:00:00',
    createdAt: '2026-08-02T14:05:00',
    placeId: 'place-jeju-airport',
    placeName: '제주공항',
    originalImageUrl: originalImage('공항'),
    generatedImageUrl: generatedImage('공항'),
    personalMessage: '드디어 제주 도착!',
    companions: [MONGI],
    isRepresentative: true,
  },
  {
    logId: 'log-1-8',
    tripId: 'trip-1',
    recordedDate: '2026-08-02',
    visitedAt: '2026-08-02T19:00:00',
    createdAt: '2026-08-02T19:05:00',
    placeId: 'place-aewol-stay',
    placeName: '애월 숙소',
    originalImageUrl: originalImage('애월 숙소'),
    generatedImageUrl: generatedImage('애월 숙소'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },

  // 한림 여름 여행 (trip-2) — 7개
  {
    logId: 'log-2-1',
    tripId: 'trip-2',
    recordedDate: '2026-07-31',
    visitedAt: '2026-07-31T16:00:00',
    createdAt: '2026-07-31T16:05:00',
    placeId: 'place-hallim-park',
    placeName: '한림공원',
    originalImageUrl: originalImage('한림공원'),
    generatedImageUrl: generatedImage('한림공원'),
    personalMessage: '한림공원 야자수 아래에서',
    companions: [MONGI],
    isRepresentative: true,
  },
  {
    logId: 'log-2-2',
    tripId: 'trip-2',
    recordedDate: '2026-07-31',
    visitedAt: '2026-07-31T12:00:00',
    createdAt: '2026-07-31T12:05:00',
    placeId: 'place-hyeopjae-beach-2',
    placeName: '협재해수욕장',
    originalImageUrl: originalImage('협재2'),
    generatedImageUrl: generatedImage('협재2'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },
  {
    logId: 'log-2-3',
    tripId: 'trip-2',
    recordedDate: '2026-07-31',
    visitedAt: '2026-07-31T09:00:00',
    createdAt: '2026-07-31T09:05:00',
    placeId: 'place-hallim-market',
    placeName: '한림 매일시장',
    originalImageUrl: originalImage('한림시장'),
    generatedImageUrl: generatedImage('한림시장'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },
  {
    logId: 'log-2-4',
    tripId: 'trip-2',
    recordedDate: '2026-07-30',
    visitedAt: '2026-07-30T18:00:00',
    createdAt: '2026-07-30T18:05:00',
    placeId: 'place-geumneung-beach',
    placeName: '금능해수욕장',
    originalImageUrl: originalImage('금능'),
    generatedImageUrl: generatedImage('금능'),
    personalMessage: '노을이 예뻤던 금능 바다',
    companions: [MONGI],
    isRepresentative: true,
  },
  {
    logId: 'log-2-5',
    tripId: 'trip-2',
    recordedDate: '2026-07-30',
    visitedAt: '2026-07-30T10:00:00',
    createdAt: '2026-07-30T10:05:00',
    placeId: 'place-hallim-cafe',
    placeName: '한림 카페거리',
    originalImageUrl: originalImage('한림카페'),
    generatedImageUrl: generatedImage('한림카페'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },
  {
    logId: 'log-2-6',
    tripId: 'trip-2',
    recordedDate: '2026-07-29',
    visitedAt: '2026-07-29T15:00:00',
    createdAt: '2026-07-29T15:05:00',
    placeId: 'place-biyangdo-ferry',
    placeName: '비양도 선착장',
    originalImageUrl: originalImage('비양도'),
    generatedImageUrl: generatedImage('비양도'),
    personalMessage: '비양도 가는 배 위에서',
    companions: [MONGI],
    isRepresentative: true,
  },
  {
    logId: 'log-2-7',
    tripId: 'trip-2',
    recordedDate: '2026-07-29',
    visitedAt: '2026-07-29T10:00:00',
    createdAt: '2026-07-29T10:05:00',
    placeId: 'place-hallim-stay',
    placeName: '한림 숙소',
    originalImageUrl: originalImage('한림숙소'),
    generatedImageUrl: generatedImage('한림숙소'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },

  // 성산 일출 여행 (trip-3) — 5개
  {
    logId: 'log-3-1',
    tripId: 'trip-3',
    recordedDate: '2026-06-14',
    visitedAt: '2026-06-14T06:00:00',
    createdAt: '2026-06-14T06:10:00',
    placeId: 'place-seongsan-ilchulbong',
    placeName: '성산일출봉',
    originalImageUrl: originalImage('성산일출봉'),
    generatedImageUrl: generatedImage('성산일출봉'),
    personalMessage: '몽이, 코코와 함께 본 일출',
    companions: [MONGI, KOKO],
    isRepresentative: true,
  },
  {
    logId: 'log-3-2',
    tripId: 'trip-3',
    recordedDate: '2026-06-14',
    visitedAt: '2026-06-14T10:00:00',
    createdAt: '2026-06-14T10:05:00',
    placeId: 'place-gwangchigi-beach',
    placeName: '광치기해변',
    originalImageUrl: originalImage('광치기'),
    generatedImageUrl: generatedImage('광치기'),
    personalMessage: null,
    companions: [MONGI, KOKO],
    isRepresentative: false,
  },
  {
    logId: 'log-3-3',
    tripId: 'trip-3',
    recordedDate: '2026-06-13',
    visitedAt: '2026-06-13T14:00:00',
    createdAt: '2026-06-13T14:05:00',
    placeId: 'place-udo-ferry',
    placeName: '우도 선착장',
    originalImageUrl: originalImage('우도'),
    generatedImageUrl: generatedImage('우도'),
    personalMessage: '우도 가는 배에서 코코가 신났다',
    companions: [KOKO],
    isRepresentative: true,
  },
  {
    logId: 'log-3-4',
    tripId: 'trip-3',
    recordedDate: '2026-06-13',
    visitedAt: '2026-06-13T09:00:00',
    createdAt: '2026-06-13T09:05:00',
    placeId: 'place-seongsan-cafe',
    placeName: '성산 카페',
    originalImageUrl: originalImage('성산카페'),
    generatedImageUrl: generatedImage('성산카페'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },
  {
    logId: 'log-3-5',
    tripId: 'trip-3',
    recordedDate: '2026-06-12',
    visitedAt: '2026-06-12T13:00:00',
    createdAt: '2026-06-12T13:05:00',
    placeId: 'place-seongsan-stay',
    placeName: '성산 숙소',
    originalImageUrl: originalImage('성산숙소'),
    generatedImageUrl: generatedImage('성산숙소'),
    personalMessage: null,
    companions: [MONGI, KOKO],
    isRepresentative: true,
  },

  // 서귀포 봄 산책 (trip-4) — 4개
  {
    logId: 'log-4-1',
    tripId: 'trip-4',
    recordedDate: '2026-04-06',
    visitedAt: '2026-04-06T11:00:00',
    createdAt: '2026-04-06T11:05:00',
    placeId: 'place-jeongbang-falls',
    placeName: '정방폭포',
    originalImageUrl: originalImage('정방폭포'),
    generatedImageUrl: generatedImage('정방폭포'),
    personalMessage: '코코와 함께 본 폭포',
    companions: [KOKO],
    isRepresentative: true,
  },
  {
    logId: 'log-4-2',
    tripId: 'trip-4',
    recordedDate: '2026-04-06',
    visitedAt: '2026-04-06T09:00:00',
    createdAt: '2026-04-06T09:05:00',
    placeId: 'place-seogwipo-market',
    placeName: '서귀포 매일올레시장',
    originalImageUrl: originalImage('서귀포시장'),
    generatedImageUrl: generatedImage('서귀포시장'),
    personalMessage: null,
    companions: [KOKO],
    isRepresentative: false,
  },
  {
    logId: 'log-4-3',
    tripId: 'trip-4',
    recordedDate: '2026-04-05',
    visitedAt: '2026-04-05T16:00:00',
    createdAt: '2026-04-05T16:05:00',
    placeId: 'place-oedolgae',
    placeName: '외돌개',
    originalImageUrl: originalImage('외돌개'),
    generatedImageUrl: generatedImage('외돌개'),
    personalMessage: '외돌개 산책길, 봄바람이 좋았다',
    companions: [KOKO],
    isRepresentative: true,
  },
  {
    logId: 'log-4-4',
    tripId: 'trip-4',
    recordedDate: '2026-04-05',
    visitedAt: '2026-04-05T10:00:00',
    createdAt: '2026-04-05T10:05:00',
    placeId: 'place-seogwipo-stay',
    placeName: '서귀포 숙소',
    originalImageUrl: originalImage('서귀포숙소'),
    generatedImageUrl: generatedImage('서귀포숙소'),
    personalMessage: null,
    companions: [KOKO],
    isRepresentative: false,
  },

  // 여행에 연결되지 않은 개별 기록 (소소한 제주 기록, 2026년 8월) — 3개
  {
    logId: 'log-u-1',
    tripId: null,
    recordedDate: '2026-08-20',
    visitedAt: '2026-08-20T17:00:00',
    createdAt: '2026-08-20T17:05:00',
    placeId: 'place-jeju-city-park',
    placeName: '동네 공원',
    originalImageUrl: originalImage('동네공원'),
    generatedImageUrl: generatedImage('동네공원'),
    personalMessage: '동네 산책도 소중한 기록',
    companions: [MONGI],
    isRepresentative: true,
  },
  {
    logId: 'log-u-2',
    tripId: null,
    recordedDate: '2026-08-15',
    visitedAt: null,
    createdAt: '2026-08-15T20:00:00',
    placeId: null,
    placeName: '집',
    originalImageUrl: originalImage('집'),
    generatedImageUrl: generatedImage('집'),
    personalMessage: null,
    companions: [KOKO],
    isRepresentative: false,
  },
  {
    logId: 'log-u-3',
    tripId: null,
    recordedDate: '2026-08-10',
    visitedAt: null,
    createdAt: '2026-08-10T08:00:00',
    placeId: null,
    placeName: '동네 카페',
    originalImageUrl: originalImage('동네카페'),
    generatedImageUrl: generatedImage('동네카페'),
    personalMessage: null,
    companions: [MONGI],
    isRepresentative: false,
  },
];

/** 로그 정렬 기준: visitedAt 우선, 없으면 createdAt */
function logTimestamp(log: TravelLog): string {
  return log.visitedAt ?? log.createdAt;
}

function sortLogsDescending(logs: TravelLog[]): TravelLog[] {
  return [...logs].sort((a, b) => logTimestamp(b).localeCompare(logTimestamp(a)));
}

const PREVIEW_LOG_COUNT = 4;

function buildTrip(meta: TripMeta): Trip {
  const logs = mockLogs.filter((log) => log.tripId === meta.tripId);
  const previewLogs = sortLogsDescending(logs).slice(0, PREVIEW_LOG_COUNT);

  return { ...meta, logCount: logs.length, previewLogs };
}

export const mockTrips: Trip[] = tripMetaList.map(buildTrip);

const ungroupedMeta = { groupId: 'ungrouped-2026-08', year: 2026, month: 8 };

function buildUngroupedGroup(): UngroupedLogGroup {
  const logs = mockLogs.filter((log) => log.tripId === null);
  const previewLogs = sortLogsDescending(logs).slice(0, PREVIEW_LOG_COUNT);

  return { ...ungroupedMeta, logCount: logs.length, previewLogs };
}

export const mockUngroupedGroup: UngroupedLogGroup = buildUngroupedGroup();

const FETCH_DELAY_MS = 600;

/**
 * TODO: 실제 여행 기록 API 연동 시 이 함수 내부를 apiClient 호출로 교체
 * 정렬 기준: 여행 시작일 내림차순, 여행에 연결되지 않은 기록 그룹은 항상 마지막.
 */
export function fetchTravelLogItems(): Promise<TravelLogListItem[]> {
  const sortedTrips = [...mockTrips].sort((a, b) => b.startDate.localeCompare(a.startDate));

  const items: TravelLogListItem[] = [
    ...sortedTrips.map((trip) => ({ kind: 'trip' as const, trip })),
    { kind: 'ungrouped' as const, group: mockUngroupedGroup },
  ];

  return new Promise((resolve) => {
    setTimeout(() => resolve(items), FETCH_DELAY_MS);
  });
}

/** 여행 모아보기 화면 헤더용 (제목·기간·기록 수) */
export function fetchTripDetail(tripId: string): Promise<Trip | null> {
  const trip = mockTrips.find((candidate) => candidate.tripId === tripId) ?? null;

  return new Promise((resolve) => {
    setTimeout(() => resolve(trip), FETCH_DELAY_MS);
  });
}

/** TODO: 실제 API 연동 시 GET /trips/{tripId}/logs 호출로 교체 */
export function fetchTripLogs(tripId: string): Promise<TravelLog[]> {
  const logs = mockLogs.filter((log) => log.tripId === tripId);

  return new Promise((resolve) => {
    setTimeout(() => resolve(logs), FETCH_DELAY_MS);
  });
}

/**
 * TODO: 실제 API 연동 시 PATCH /logs/{logId} 호출로 교체
 * 지금은 세션 내 메모리에만 반영되는 목업 mutation. mockLogs 배열을 직접 갱신한다.
 */
export function updatePersonalMessage(logId: string, message: string | null): Promise<TravelLog> {
  const index = mockLogs.findIndex((log) => log.logId === logId);

  if (index === -1) {
    return Promise.reject(new Error(`로그를 찾을 수 없습니다: ${logId}`));
  }

  mockLogs[index] = { ...mockLogs[index], personalMessage: message };
  const updated = mockLogs[index];

  return new Promise((resolve) => {
    setTimeout(() => resolve(updated), 300);
  });
}
