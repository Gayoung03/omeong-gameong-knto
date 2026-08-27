/**
 * 서버 여행기록 응답 → 앱 여행기록 타입 변환.
 *
 * 서버와 앱이 같은 것을 다른 이름으로 부르는 곳을 **여기 한 곳에서만** 흡수한다.
 * 화면·훅은 `@/src/types/travelLog` 만 보고, 서버 생김새를 몰라야 한다.
 * (`features/trips/api/routeAdapter.ts` 와 같은 방식이다.)
 *
 * | 서버          | 앱          |
 * | ------------- | ----------- |
 * | `id`          | `logId`     |
 * | `routeId`     | `tripId`    |
 * | `placeNameSnapshot` | `placeName` |
 * | `kind: 'route'`     | `kind: 'trip'` |
 *
 * `writingStyle` `mood` `generationStatus` 는 앱 타입에 자리가 없어 버린다.
 * 화면이 쓰기 시작하면 `types/travelLog.ts` 에 필드를 넣고 여기서 채우면 된다.
 */

import type {
  Trip,
  TravelLog,
  TravelLogListItem,
  TravelLogPetSnapshot,
  UngroupedLogGroup,
} from '@/src/types/travelLog';

import type {
  TravelLogCompanionResponse,
  TravelLogGroupResponse,
  TravelLogItemResponse,
  TravelLogMonthSummaryResponse,
  TravelLogRouteSummaryResponse,
} from '../types/travelLogApi';

/**
 * 반려동물 스냅샷.
 *
 * 앱 타입의 `petId` 는 필수인데 서버는 프로필을 완전히 지운 경우 null 을 준다.
 * 이름·사진은 남아 있어 화면은 그대로 그릴 수 있으므로 빈 문자열로 채운다.
 * **동일 개체 판단에 쓰면 안 된다** — 지워진 것끼리 같아 보인다.
 */
function toPetSnapshot(companion: TravelLogCompanionResponse): TravelLogPetSnapshot {
  return {
    petId: companion.petId ?? '',
    nameSnapshot: companion.nameSnapshot,
    profileImageSnapshot: companion.profileImageSnapshot ?? undefined,
  };
}

/**
 * 기록 한 건.
 *
 * `generatedImageUrl` 은 생성이 끝나기 전이면 서버가 null 을 준다. 앱 타입은
 * 항상 있다고 돼 있고 목록·팝업·공유가 전부 이 필드를 쓰므로, 없으면 원본으로
 * 대신 채워 화면이 빈 사진으로 깨지지 않게 한다.
 */
export function toTravelLog(response: TravelLogItemResponse): TravelLog {
  return {
    logId: response.id,
    tripId: response.routeId,
    recordedDate: response.recordedDate,
    visitedAt: response.visitedAt,
    createdAt: response.createdAt,
    placeId: response.placeId,
    placeName: response.placeNameSnapshot,
    originalImageUrl: response.originalImageUrl,
    generatedImageUrl: response.generatedImageUrl ?? response.originalImageUrl,
    personalMessage: response.personalMessage,
    companions: response.companions.map(toPetSnapshot),
    isRepresentative: response.isRepresentative,
  };
}

/**
 * 여행 그룹.
 *
 * `placeName` 은 앱에서 장소명 검색의 대상이다. 서버는 그 여행의 가장 최근
 * 기록 장소를 내려주고, 기록이 없으면 null 이라 빈 문자열로 둔다.
 */
function toTrip(response: TravelLogRouteSummaryResponse): Trip {
  return {
    tripId: response.id,
    title: response.title,
    placeName: response.placeNameSnapshot ?? '',
    startDate: response.startDate ?? '',
    endDate: response.endDate ?? '',
    companions: response.companions.map(toPetSnapshot),
    logCount: response.logCount,
    previewLogs: response.previewLogs.map(toTravelLog),
  };
}

/**
 * 월 그룹.
 *
 * 앱 타입의 `groupId` 는 서버에 없다. 목록에서 각 줄을 구분하는 열쇠로만
 * 쓰이므로 연·월을 붙여 만든다 — 같은 달은 한 그룹뿐이라 겹치지 않는다.
 */
function toUngroupedGroup(response: TravelLogMonthSummaryResponse): UngroupedLogGroup {
  return {
    groupId: `${response.year}-${String(response.month).padStart(2, '0')}`,
    year: response.year,
    month: response.month,
    logCount: response.logCount,
    previewLogs: response.previewLogs.map(toTravelLog),
  };
}

/** 목록 한 줄. 서버의 `route` 를 앱의 `trip` 으로 바꾼다 */
export function toTravelLogListItem(response: TravelLogGroupResponse): TravelLogListItem {
  return response.kind === 'route'
    ? { kind: 'trip', trip: toTrip(response.route) }
    : { kind: 'ungrouped', group: toUngroupedGroup(response.group) };
}
