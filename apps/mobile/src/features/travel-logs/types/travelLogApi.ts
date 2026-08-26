/**
 * 서버(FastAPI) 여행기록 API 의 응답 타입.
 *
 * 정본은 `docs/api/travel-logs.md` 와 `apps/api/app/schemas/travel_log.py` 다.
 * 서버 스키마가 `alias_generator=to_camel` 을 쓰므로 JSON 은 camelCase 로 온다.
 *
 * 화면이 쓰는 타입은 `@/src/types/travelLog` 이고 생김새가 다르다.
 * 둘 사이 변환은 `../api/travelLogAdapter.ts` 한 곳에서만 한다 — 화면은 이 파일을 몰라야 한다.
 *
 * `Server~` 접두사가 붙은 값은 DB CHECK 제약과 짝이라 **snake_case** 다 (`dog_diary`).
 */

/** 이미지에 얹는 글 말투. 앱 타입에는 대응 값이 없어 어댑터가 버린다 */
export type ServerWritingStyle = 'dog_diary' | 'jeju_dialect';

/** 그때의 기분. 앱 타입에는 대응 값이 없어 어댑터가 버린다 */
export type ServerMomentMood = 'happy' | 'excited' | 'relaxed' | 'bittersweet';

/**
 * AI 이미지 생성 진행 상태.
 * `completed` 가 아니면 `generatedImageUrl` 이 아직 null 일 수 있다.
 */
export type ServerGenerationStatus =
  | 'idle'
  | 'uploading'
  | 'generating'
  | 'completed'
  | 'failed';

/**
 * 함께한 반려동물 스냅샷.
 *
 * `petId` 는 서버에서 `ON DELETE SET NULL` 이라 **프로필을 완전히 지우면 null** 이다.
 * 그래도 이름·사진은 남는다.
 */
export type TravelLogCompanionResponse = {
  petId: string | null;
  nameSnapshot: string;
  profileImageSnapshot: string | null;
};

/** 기록 한 건. 목록·상세·미리보기가 모두 이 생김새다 */
export type TravelLogItemResponse = {
  id: string;
  routeId: string | null;
  placeId: string | null;
  placeNameSnapshot: string;
  recordedDate: string;
  visitedAt: string | null;
  originalImageUrl: string;
  /** 생성 전이면 null. 어댑터가 원본으로 대신 채운다 */
  generatedImageUrl: string | null;
  writingStyle: ServerWritingStyle;
  mood: ServerMomentMood | null;
  generationStatus: ServerGenerationStatus;
  personalMessage: string | null;
  isRepresentative: boolean;
  companions: TravelLogCompanionResponse[];
  createdAt: string;
};

/** GET /travel-logs */
export type TravelLogListResponse = {
  items: TravelLogItemResponse[];
  total: number;
  limit: number;
  offset: number;
};

/** GET /travel-logs/groups 의 여행 그룹 */
export type TravelLogRouteSummaryResponse = {
  id: string;
  title: string;
  startDate: string | null;
  endDate: string | null;
  placeNameSnapshot: string | null;
  /** 여행 **자체**의 반려동물. 각 기록의 companions 와는 다른 데이터다 */
  companions: TravelLogCompanionResponse[];
  logCount: number;
  previewLogs: TravelLogItemResponse[];
};

/** GET /travel-logs/groups 의 월 그룹 (여행에 속하지 않은 개별 기록) */
export type TravelLogMonthSummaryResponse = {
  year: number;
  /** 1-12 */
  month: number;
  logCount: number;
  previewLogs: TravelLogItemResponse[];
};

/** 서버는 `route`, 앱은 `trip` 이라 부른다. 어댑터가 바꾼다 */
export type TravelLogGroupResponse =
  | { kind: 'route'; route: TravelLogRouteSummaryResponse }
  | { kind: 'ungrouped'; group: TravelLogMonthSummaryResponse };

/** GET /travel-logs/groups */
export type TravelLogGroupsResponse = {
  items: TravelLogGroupResponse[];
  total: number;
  limit: number;
  offset: number;
};

/**
 * POST /travel-logs 로 보내는 것.
 *
 * `originalImageUrl` 은 `POST /uploads`(purpose=travel_log)로 먼저 올리고 받은 주소다.
 * `generatedImageUrl` 은 앱이 보내지 않는다 — 서버가 만들어 채운다.
 */
export type TravelLogCreateRequest = {
  routeId?: string | null;
  placeId?: string;
  /** placeId 가 없으면 필수 */
  placeName?: string;
  recordedDate: string;
  visitedAt?: string | null;
  originalImageUrl: string;
  writingStyle: ServerWritingStyle;
  mood?: ServerMomentMood | null;
  personalMessage?: string | null;
  petIds?: string[];
};

/** POST /travel-logs/{logId}/regenerate. 둘 다 생략하면 기존 값으로 다시 만든다 */
export type TravelLogRegenerateRequest = {
  writingStyle?: ServerWritingStyle;
  mood?: ServerMomentMood | null;
};

/**
 * POST /travel-logs 의 202 응답, 그리고 GET /travel-logs/{logId}/status.
 *
 * 생성은 오래 걸려서 서버가 "접수했다"고만 먼저 답한다.
 * 앱은 완료될 때까지 status 를 반복해서 확인한다.
 */
export type TravelLogGenerationStatusResponse = {
  id: string;
  generationStatus: ServerGenerationStatus;
  /** 완료됐을 때만 채워진다 */
  generatedImageUrl: string | null;
};

/** PATCH /travel-logs/{logId} 로 보내는 것. 보낸 필드만 수정된다 */
export type TravelLogUpdateRequest = {
  personalMessage?: string | null;
  recordedDate?: string;
  visitedAt?: string | null;
  placeId?: string;
  placeName?: string;
  mood?: ServerMomentMood | null;
  isRepresentative?: boolean;
  petIds?: string[];
};
