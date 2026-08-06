/**
 * 기록 당시의 반려동물 정보 스냅샷.
 * 프로필을 수정하거나 지워도 과거 기록의 이름·사진이 따라 바뀌지 않도록,
 * 화면은 살아있는 Pet을 다시 조회하지 않고 이 스냅샷만 보고 그린다.
 * 동일 개체 판단은 언제나 petId로만 한다(이름은 중복될 수 있고 변경될 수도 있다).
 */
export interface TravelLogPetSnapshot {
  petId: string;
  nameSnapshot: string;
  profileImageSnapshot?: string;
}

/** 사용자가 남긴 순간 하나. 원본 사진과 손글씨·장식이 적용된 완성 이미지를 구분한다. */
export interface TravelLog {
  logId: string;
  /** null이면 특정 여행에 연결되지 않은 개별 기록 */
  tripId: string | null;
  /** 날짜 그룹핑 기준. ISO 날짜 문자열 (YYYY-MM-DD) */
  recordedDate: string;
  /** 방문 시각. 있으면 정렬 1순위로 사용한다. ISO datetime */
  visitedAt: string | null;
  /** 정렬 2순위 (visitedAt이 없을 때). ISO datetime */
  createdAt: string;
  placeId: string | null;
  placeName: string;
  /** 사용자가 업로드한 원본. 재생성/편집 용도로만 쓰고 목록·팝업에는 노출하지 않는다. */
  originalImageUrl: string;
  /** 손글씨·장식이 적용된 완성 이미지. 콜라주·목록·팝업·공유·저장 전부 이 필드를 쓴다. */
  generatedImageUrl: string;
  /** 사용자가 선택적으로 남긴 한 줄. AI가 이미지에 그린 손글씨 문구와는 별개 필드. */
  personalMessage: string | null;
  /** 기록 시점에 함께한 반려동물 스냅샷. DB의 travel_log_pets 행에 대응한다. */
  companions: TravelLogPetSnapshot[];
  /** 날짜 그룹의 대표 로그 여부. 지정 UI는 이번 범위 밖, 데이터만 준비. */
  isRepresentative: boolean;
}

export interface Trip {
  tripId: string;
  title: string;
  /** 장소명 검색이 대상으로 삼는 필드 */
  placeName: string;
  /** ISO 날짜 문자열 (YYYY-MM-DD) */
  startDate: string;
  endDate: string;
  /**
   * 여행 자체에 설정된 동행 반려동물 스냅샷. 로그가 하나도 없어도 존재할 수 있는
   * 독립 여행 단위이므로 하위 로그에서 계산하지 않고 별도로 보관한다(DB의 trip_pets).
   * 하위 로그의 companions와 별개 데이터이므로 어느 한쪽만 임의로 고치지 않는다.
   */
  companions: TravelLogPetSnapshot[];
  logCount: number;
  /** 메인 화면 콜라주용 미리보기. 항상 실제 로그(같은 logId)에서 가져온다. */
  previewLogs: TravelLog[];
}

/** 여행에 연결되지 않은 개별 로그를 월 단위로 묶은 그룹 */
export interface UngroupedLogGroup {
  groupId: string;
  year: number;
  /** 1-12 */
  month: number;
  logCount: number;
  previewLogs: TravelLog[];
}

export type TravelLogListItem =
  | { kind: 'trip'; trip: Trip }
  | { kind: 'ungrouped'; group: UngroupedLogGroup };

export interface DateRange {
  /** ISO 날짜 문자열 (YYYY-MM-DD) */
  start: string;
  end: string;
}

export interface TravelLogFilters {
  placeQuery: string;
  dateRange: DateRange | null;
  petIds: string[];
}
